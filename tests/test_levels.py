"""Проверки корректности уровня, сохранения и загрузки."""

import json
import random

import pytest

from minotaur import constants
from minotaur.custom_types import Cell, Level, Player
from minotaur.exceptions import LevelError
from minotaur.generator import add_loops, init_map_gen, making_labyrinth
from minotaur.levels import (
    load_level, place_exit_and_player,
    save_level, validate_level,
)


@pytest.fixture
def level():
    """Уровень со всеми типами объектов и действующими эффектами."""
    return Level(
        maze=[list(row) for row in
              ['#######', '#.....#', '#.....#', '#.....#', '#######']],
        players={1: Player(nick='Vladimir', pos=Cell(1, 1),
                           last_played_round=None, torch_active=True)},
        exit=Cell(3, 5), key=Cell(1, 5),
        monsters=[('H', Cell(2, 4)), ('W', Cell(3, 1))],
        bonuses={Cell(1, 2): '*', Cell(1, 3): '^', Cell(1, 4): '?'},
        freeze_turns=2,
    )


def test_round_trip(level, tmp_path):
    """Все поля и типы восстанавливаются без изменения исходного уровня."""
    path = tmp_path / 'уровень.json'
    save_level(level, path)
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['maze'] == level.maze
    loaded = load_level(path)
    assert loaded == level
    assert type(loaded.players[1].pos) is Cell
    assert type(loaded.exit) is Cell
    assert type(loaded.key) is Cell
    assert type(loaded.monsters[0][1]) is Cell
    for cell in loaded.bonuses:
        assert type(cell) is Cell
    loaded.maze[1][1] = '#'
    assert level.maze[1][1] == '.'


def test_overwrite(level, tmp_path):
    """После перезаписи исчезают подобранные объекты и истёкшие эффекты."""
    path = tmp_path / 'level.json'
    save_level(level, path)
    level.key = None
    level.monsters.clear()
    level.bonuses.clear()
    level.freeze_turns = 0
    level.players[1].torch_active = False
    level.players[1].pos = Cell(3, 4)
    save_level(level, path)
    assert load_level(path) == level


def test_manual_file_without_effects(tmp_path):
    """Файл можно написать вручную; пропущенные эффекты выключены."""
    path = tmp_path / 'manual.json'
    path.write_text(json.dumps({
        'maze': [list('#####'), list('#...#'), list('#.#.#'),
                 list('#...#'), list('#####')],
        'players': {
            '1': {
                'nick': 'Vladimir',
                'pos': [1, 1],
                'last_played_round': -1,
            }
        },
        'exit': [3, 3], 'key': None,
        'monsters': [], 'bonuses': [],
    }), encoding='utf-8')
    loaded = load_level(path)
    assert loaded.freeze_turns == 0
    assert loaded.players[1].torch_active is False
    assert loaded.key is None


@pytest.mark.parametrize('text', ['', '{', '{}', 'null', '[]', '42'])
def test_invalid_file(tmp_path, text):
    """Неверный JSON или отсутствие обязательных полей дают LevelError."""
    path = tmp_path / 'broken.json'
    path.write_text(text, encoding='utf-8')
    with pytest.raises(LevelError):
        load_level(path)


def test_invalid_encoding(tmp_path):
    """Файл не в UTF-8 отклоняется с ошибкой проекта."""
    path = tmp_path / 'broken.json'
    path.write_bytes(b'\xff')
    with pytest.raises(LevelError):
        load_level(path)


def test_level_validation_is_separate(level, tmp_path):
    """Сохранение не проверяет уровень, но загрузка отклоняет неверный."""
    path = tmp_path / 'level.json'
    level.maze = []
    level.players[1].pos = Cell(-1, -1)
    level.freeze_turns = -1
    save_level(level, path)
    with pytest.raises(LevelError):
        load_level(path)


def test_file_errors(level, tmp_path):
    """Отсутствующий файл и невозможность записи дают LevelError."""
    with pytest.raises(LevelError):
        load_level(tmp_path / 'missing.json')
    with pytest.raises(LevelError):
        save_level(level, tmp_path)
    with pytest.raises(LevelError):
        save_level(None, tmp_path / 'invalid.json')


@pytest.mark.parametrize('from_file', [False, True])
def test_validate_level(level, tmp_path, from_file):
    """Проверка принимает Level и путь к файлу, не меняет исходные данные."""
    path = tmp_path / 'level.json'
    save_level(level, path)
    before = path.read_bytes()
    source = level
    if from_file:
        source = path
    data = validate_level(source)
    assert data['maze'] == level.maze
    assert path.read_bytes() == before
    assert load_level(path) == level


@pytest.mark.parametrize('from_file', [False, True])
@pytest.mark.parametrize('field, value', [
    ('maze', []),
    ('maze', ['#####'] * 5),
    ('maze', [list('#####'), list('##')]),
    ('maze', [list('#######'), list('#P....#'), list('#.....#'),
              list('#.....#'), list('#######')]),
    ('maze', [list('###.###'), list('#.....#'), list('#.....#'),
              list('#.....#'), list('#######')]),
    ('maze', [list('#######'), list('#.#...#'), list('#######'),
              list('#.....#'), list('#######')]),
    ('player', Cell(True, 1)), ('player', Cell(1.5, 1)),
    ('player', Cell(0, 0)), ('player', Cell(100, 1)),
    ('exit', None), ('key', Cell(0, 0)),
    ('monsters', [('X', Cell(1, 2))]),
    ('monsters', [('H', Cell(0, 0))]),
    ('bonuses', {Cell(1, 2): 'X'}),
    ('freeze_turns', -1), ('freeze_turns', True),
    ('torch_active', 1),
])
def test_validate_invalid_level(level, tmp_path, from_file, field, value):
    """Одинаковые ошибки отклоняются в объекте и в файле."""
    if field == 'player':
        level.players[1].pos = value
    elif field == 'torch_active':
        level.players[1].torch_active = value
    else:
        setattr(level, field, value)
    source = level
    if from_file:
        source = tmp_path / 'level.json'
        save_level(level, source)
    with pytest.raises(LevelError):
        validate_level(source)
    if from_file:
        with pytest.raises(LevelError):
            load_level(source)


def test_duplicate_bonuses(level, tmp_path):
    """Повтор координаты бонуса в JSON не теряется при создании словаря."""
    path = tmp_path / 'level.json'
    save_level(level, path)
    data = json.loads(path.read_text(encoding='utf-8'))
    data['bonuses'].append(data['bonuses'][0])
    path.write_text(json.dumps(data), encoding='utf-8')
    message = 'Координаты бонуса и бонуса совпадают'
    with pytest.raises(LevelError, match=message):
        load_level(path)


@pytest.mark.parametrize('from_file', [False, True])
@pytest.mark.parametrize('case, names', [
    ('player_exit', 'выхода и игрока'),
    ('player_key', 'ключа и игрока'),
    ('exit_key', 'ключа и выхода'),
    ('player_monster', 'монстра и игрока'),
    ('exit_monster', 'монстра и выхода'),
    ('key_monster', 'монстра и ключа'),
    ('player_bonus', 'бонуса и игрока'),
    ('exit_bonus', 'бонуса и выхода'),
    ('key_bonus', 'бонуса и ключа'),
    ('monster_bonus', 'бонуса и монстра'),
    ('two_monsters', 'монстра и монстра'),
    ('player_monster_bonus', 'монстра и игрока'),
])
def test_overlapping_objects(level, tmp_path, from_file, case, names):
    """Любая пара объектов отклоняется с указанием обоих типов."""
    if case == 'player_exit':
        level.exit = level.players[1].pos
    if case == 'player_key':
        level.key = level.players[1].pos
    if case == 'exit_key':
        level.key = level.exit
    if case in ('player_monster', 'player_monster_bonus'):
        level.monsters[0] = ('H', level.players[1].pos)
    if case == 'exit_monster':
        level.monsters[0] = ('H', level.exit)
    if case == 'key_monster':
        level.monsters[0] = ('H', level.key)
    if case in ('player_bonus', 'player_monster_bonus'):
        level.bonuses[level.players[1].pos] = '*'
    if case == 'exit_bonus':
        level.bonuses[level.exit] = '*'
    if case == 'key_bonus':
        level.bonuses[level.key] = '*'
    if case == 'monster_bonus':
        level.bonuses[level.monsters[0][1]] = '*'
    if case == 'two_monsters':
        level.monsters[1] = ('W', level.monsters[0][1])
    source = level
    if from_file:
        source = tmp_path / 'overlap.json'
        save_level(level, source)
    message = f'Координаты {names} совпадают'
    with pytest.raises(LevelError, match=message):
        validate_level(source)
    if from_file:
        with pytest.raises(LevelError, match=message):
            load_level(source)


def test_validation_error_message(level, tmp_path):
    """Ошибку проверки не оборачивают повторно ни проверка, ни загрузка."""
    level.maze = []
    path = tmp_path / 'invalid.json'
    save_level(level, path)
    expected = 'Карта должна содержать не меньше пяти строк.'
    with pytest.raises(LevelError) as direct_error:
        validate_level(level)
    with pytest.raises(LevelError) as file_error:
        load_level(path)
    assert str(direct_error.value) == expected
    assert str(file_error.value) == expected


def test_load_preserves_level_error(monkeypatch):
    """Загрузка передаёт тот же объект LevelError, который дала проверка."""
    error = LevelError('Ошибка проверки уровня.')

    def fail_validation(source):
        """Имитировать ошибку проверки файла."""
        raise error

    monkeypatch.setattr('minotaur.levels.validate_level', fail_validation)
    with pytest.raises(LevelError) as caught:
        load_level('unused.json')
    assert caught.value is error


def test_generation_to_level_file(tmp_path):
    """Карта и координаты проходят все этапы без поиска объектов в матрице."""
    rng = random.Random(2)
    maze = init_map_gen(0)
    player, exit_pos = place_exit_and_player(maze, rng)
    making_labyrinth(maze, player, exit_pos, rng)
    add_loops(maze, constants.LEVEL_CONTENTS[0][3], rng)
    for row in maze:
        for symbol in row:
            assert symbol in (constants.FILE_AIR, constants.FILE_WALL)
    level = Level(
        maze=maze,
        exit=exit_pos,
        key=None,
        players={
            1: Player(nick='Vladimir', pos=player,
                      last_played_round=None)
        },
    )
    validate_level(level)
    path = tmp_path / 'generated.json'
    save_level(level, path)
    assert load_level(path) == level


@pytest.mark.parametrize('from_file', [False, True])
def test_compass_is_saved_per_player(level, tmp_path, from_file):
    """Компас хранится у каждого игрока и проверяется как булево."""
    path = tmp_path / 'level.json'
    level.players[2] = Player(pos=Cell(2, 2), compass_active=True)
    save_level(level, path)
    loaded = load_level(path)
    assert loaded.players[1].compass_active is False
    assert loaded.players[2].compass_active is True
    level.players[2].compass_active = 1
    source = level
    if from_file:
        source = tmp_path / 'bad.json'
        save_level(level, source)
    with pytest.raises(LevelError, match='состояние игрока'):
        validate_level(source)


def test_player_id_is_dict_key(level, tmp_path):
    """Идентификатор игрока задаётся только ключом словаря players."""
    path = tmp_path / 'level.json'
    save_level(level, path)
    data = json.loads(path.read_text(encoding='utf-8'))
    assert 'id' not in data['players']['1']
    data['players']['abc'] = data['players'].pop('1')
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(LevelError, match='идентификатор'):
        load_level(path)


def test_is_key_taken(level):
    """Ключ общий: после подбора любым игроком он поднят для всех."""
    assert level.is_key_taken is False
    level.key = None
    assert level.is_key_taken is True

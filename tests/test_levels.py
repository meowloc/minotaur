"""Проверки файлов уровня и сохранения эффектов."""

import json

import pytest

from minotaur.custom_types import Cell, Level
from minotaur.exceptions import LevelError
from minotaur.levels import load_level, save_level, validate_level


@pytest.fixture
def level():
    """Уровень со всеми типами объектов и действующими эффектами."""
    return Level(
        maze=[list(row) for row in
              ['#######', '#.....#', '#.....#', '#.....#', '#######']],
        player=Cell(1, 1), exit=Cell(3, 5), key=Cell(1, 5),
        monsters=[('H', Cell(2, 4)), ('W', Cell(3, 1))],
        bonuses={Cell(1, 2): '*', Cell(1, 3): '^', Cell(1, 4): '?'},
        freeze_turns=2, torch_active=True,
    )


def test_round_trip(level, tmp_path):
    """Все поля и типы восстанавливаются без изменения исходного уровня."""
    path = tmp_path / 'уровень.json'
    save_level(level, path)
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['maze'] == level.maze
    loaded = load_level(path)
    assert loaded == level
    assert type(loaded.player) is Cell
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
    level.torch_active = False
    level.player = level.exit
    save_level(level, path)
    assert load_level(path) == level


def test_manual_file_without_effects(tmp_path):
    """Файл можно написать вручную; пропущенные эффекты выключены."""
    path = tmp_path / 'manual.json'
    path.write_text(json.dumps({
        'maze': [list('#####'), list('#...#'), list('#.#.#'),
                 list('#...#'), list('#####')],
        'player': [1, 1], 'exit': [3, 3], 'key': None,
        'monsters': [], 'bonuses': [],
    }), encoding='utf-8')
    loaded = load_level(path)
    assert loaded.freeze_turns == 0
    assert loaded.torch_active is False
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
    level.player = Cell(-1, -1)
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
    with pytest.raises(LevelError):
        load_level(path)


@pytest.mark.parametrize('from_file', [False, True])
@pytest.mark.parametrize('case', [
    'player_monster', 'player_bonus', 'monster_bonus',
    'two_monsters', 'player_monster_bonus',
])
def test_overlapping_objects(level, tmp_path, from_file, case):
    """Игрок, монстры и бонусы не могут занимать одну клетку."""
    if case in ('player_monster', 'player_monster_bonus'):
        level.monsters[0] = ('H', level.player)
    if case in ('player_bonus', 'player_monster_bonus'):
        level.bonuses[level.player] = '*'
    if case == 'monster_bonus':
        level.bonuses[level.monsters[0][1]] = '*'
    if case == 'two_monsters':
        level.monsters[1] = ('W', level.monsters[0][1])
    source = level
    if from_file:
        source = tmp_path / 'overlap.json'
        save_level(level, source)
    with pytest.raises(LevelError, match='совпадают'):
        validate_level(source)
    if from_file:
        with pytest.raises(LevelError, match='совпадают'):
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

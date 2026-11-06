"""Проверки генерации карты и расстановки объектов."""

import random

import pytest

from minotaur import constants
from minotaur.custom_types import Cell, Level, Player
from minotaur.exceptions import GenerationError, LevelError, PlaceError
from minotaur.generator import add_loops, init_map_gen, making_labyrinth
from minotaur.levels import (
    generate_level, place_exit_and_player, place_objects,
)
from minotaur.pathfinding import get_bfs_distances, get_shortest_path


def test_init_map():
    """Первый уровень состоит только из стен и имеет заданный размер."""
    height, width = constants.LEVEL_SIZES[0]
    expected = []
    for row in range(height):
        expected.append([constants.FILE_WALL] * width)

    assert init_map_gen(0) == expected


def test_init_map_invalid_level():
    """Отрицательный индекс вызывает ошибку номера уровня."""
    with pytest.raises(GenerationError, match="Недопустимый номер уровня"):
        init_map_gen(-1)


def test_place_exit_and_player():
    """Координаты выбраны вдоль стен поля 7x7, карта не изменена."""
    maze = [
        list("#######"),
        list("#######"),
        list("#######"),
        list("#######"),
        list("#######"),
        list("#######"),
        list("#######"),
    ]
    expected = []
    for row in maze:
        expected.append(row[:])

    positions = place_exit_and_player(maze, random.Random(0))

    assert all(isinstance(cell, Cell) for cell in positions)
    assert positions == (Cell(1, 5), Cell(5, 3))
    assert maze == expected


def test_placement_on_occupied_map():
    """Расстановка на занятой карте вызывает ожидаемую ошибку."""
    maze = [
        list("#####"),
        list("#.###"),
        list("#####"),
        list("#####"),
        list("#####"),
    ]
    with pytest.raises(PlaceError, match="нужна карта только из стен"):
        place_exit_and_player(maze)


def test_dfs_continues_after_exit():
    """DFS проходит через выход и открывает оставшуюся комнату."""
    maze = [
        list("#####"),
        list("#####"),
        list("#####"),
        list("#####"),
        list("#####"),
    ]
    expected = [
        list("#####"),
        list("#...#"),
        list("###.#"),
        list("#...#"),
        list("#####"),
    ]

    result = making_labyrinth(maze, Cell(1, 1), Cell(3, 3), random.Random(0))
    assert result is maze
    assert result == expected


def test_dfs_without_player_and_exit():
    """Без игрока и выхода DFS вызывает ожидаемую ошибку."""
    maze = [
        list("#####"),
        list("#####"),
        list("#####"),
        list("#####"),
        list("#####"),
    ]
    with pytest.raises(GenerationError, match="Нужны координаты"):
        making_labyrinth(maze, None, None)


def test_add_loops():
    """Одна перегородка превращается в проход; остальные клетки прежние."""
    maze = [
        list("#####"),
        list("#...#"),
        list("###.#"),
        list("#...#"),
        list("#####"),
    ]
    expected = [
        list("#####"),
        list("#...#"),
        list("#.#.#"),
        list("#...#"),
        list("#####"),
    ]
    assert add_loops(maze, 1, random.Random(0)) is maze
    assert maze == expected


def test_add_loops_between_left_and_right():
    """Открывается также перегородка между левым и правым коридором."""
    maze = [
        list("#####"),
        list("#.#.#"),
        list("#.#.#"),
        list("#...#"),
        list("#####"),
    ]
    expected = []
    for row in maze:
        expected.append(row[:])
    expected[1][2] = constants.FILE_AIR
    assert add_loops(maze, 1, random.Random(0)) == expected


def test_add_loops_zero():
    """Ноль дополнительных проходов оставляет карту прежней."""
    maze = init_map_gen(0)
    before = []
    for row in maze:
        before.append(row[:])
    assert add_loops(maze, 0) is maze
    assert maze == before


def test_add_loops_count_and_seed():
    """Открываются ровно две разные стены; seed повторяет результат."""
    results = []
    for _ in range(2):
        maze = [
            list("#######"),
            list("#.....#"),
            list("#####.#"),
            list("#.....#"),
            list("#.#####"),
            list("#.....#"),
            list("#######"),
        ]
        before = []
        for row in maze:
            before.append(row[:])
        add_loops(maze, 2, random.Random(10))
        changed = 0
        for row in range(len(maze)):
            for col in range(len(maze[row])):
                if maze[row][col] != before[row][col]:
                    assert before[row][col] == constants.FILE_WALL
                    assert maze[row][col] == constants.FILE_AIR
                    assert 0 < row < len(maze) - 1
                    assert 0 < col < len(maze[row]) - 1
                    changed += 1
        assert changed == 2
        results.append(maze)
    assert results[0] == results[1]


def test_add_loops_not_enough_walls():
    """Если нужна пара стен, а подходит одна, карта не меняется."""
    maze = [
        list("#####"),
        list("#...#"),
        list("###.#"),
        list("#...#"),
        list("#####"),
    ]
    before = []
    for row in maze:
        before.append(row[:])
    with pytest.raises(LevelError, match="Недостаточно стен"):
        add_loops(maze, 2)
    assert maze == before


def test_add_loops_does_not_extend_dfs():
    """Первый путь без подходящих перегородок не достраивается."""
    maze = [
        list("#####"),
        list("#...#"),
        list("###.#"),
        list("###.#"),
        list("#####"),
    ]
    before = []
    for row in maze:
        before.append(row[:])
    with pytest.raises(LevelError, match="Недостаточно стен"):
        add_loops(maze, 1)
    assert maze == before


@pytest.mark.parametrize('level_num', range(constants.MAX_LEVEL))
def test_full_maze_and_loops(level_num):
    """Все комнаты достижимы, а штатное число петель доступно на 300 seed."""
    height, width = constants.LEVEL_SIZES[level_num]
    room_count = ((height - 1) // 2) * ((width - 1) // 2)
    loop_count = constants.LEVEL_CONTENTS[level_num][3]
    for seed in range(300):
        rng = random.Random(seed)
        maze = init_map_gen(level_num)
        player, exit_pos = place_exit_and_player(maze, rng)
        making_labyrinth(maze, player, exit_pos, rng)

        distances = get_bfs_distances(maze, player)
        assert exit_pos in distances
        for row in range(1, height - 1, 2):
            for col in range(1, width - 1, 2):
                assert Cell(row, col) in distances
        # У дерева из N комнат ровно N - 1 открытых перегородок.
        assert len(distances) == 2 * room_count - 1

        before = [row[:] for row in maze]
        assert add_loops(maze, loop_count, rng) is maze
        changed = 0
        for row in range(height):
            for col in range(width):
                if maze[row][col] != before[row][col]:
                    assert before[row][col] == constants.FILE_WALL
                    assert maze[row][col] == constants.FILE_AIR
                    changed += 1
                if row in (0, height - 1) or col in (0, width - 1):
                    assert maze[row][col] == constants.FILE_WALL
                if row % 2 == 0 and col % 2 == 0:
                    assert maze[row][col] == constants.FILE_WALL
        assert changed == loop_count
        assert len(get_bfs_distances(maze, player)) == (
            2 * room_count - 1 + loop_count
        )


def test_full_generation_seed():
    """Один seed повторяет карту и координаты всей цепочки генерации."""
    results = []
    for _ in range(2):
        rng = random.Random(10)
        maze = init_map_gen(0)
        player, exit_pos = place_exit_and_player(maze, rng)
        making_labyrinth(maze, player, exit_pos, rng)
        add_loops(maze, constants.LEVEL_CONTENTS[0][3], rng)
        results.append((maze, player, exit_pos))
    assert results[0] == results[1]


def test_dfs_exit_at_start():
    """Даже при совпадении старта и выхода DFS обходит все комнаты."""
    maze = init_map_gen(0)
    making_labyrinth(maze, Cell(1, 1), Cell(1, 1), random.Random(0))
    distances = get_bfs_distances(maze, Cell(1, 1))
    for row in range(1, len(maze) - 1, 2):
        for col in range(1, len(maze[0]) - 1, 2):
            assert Cell(row, col) in distances


def test_add_loops_invalid_count():
    """Некорректное число проходов вызывает ошибку."""
    for count in [-1, 1.5, "2", True]:
        with pytest.raises(LevelError, match="Число дополнительных"):
            add_loops(init_map_gen(0), count)


def test_add_loops_invalid_map():
    """Пустая или неровная карта вызывает ошибку."""
    with pytest.raises(LevelError, match="Размеры карты"):
        add_loops([], 1)
    maze = init_map_gen(0)
    maze[1].pop()
    with pytest.raises(LevelError, match="Строки карты"):
        add_loops(maze, 1)


@pytest.mark.parametrize('player, exit_pos', [
    (Cell(0, 1), Cell(3, 3)),
    (Cell(1, 1), Cell(2, 3)),
    (Cell(True, 1), Cell(3, 3)),
])
def test_dfs_invalid_coordinates(player, exit_pos):
    """Неверные координаты отклоняются до изменения карты."""
    maze = init_map_gen(0)
    with pytest.raises(GenerationError):
        making_labyrinth(maze, player, exit_pos)
    assert maze == init_map_gen(0)


@pytest.mark.parametrize('level_num', range(constants.MAX_LEVEL))
def test_objects_on_generated_maps(level_num):
    """Расстановка соблюдает расстояния, числа и доступность объектов."""
    for seed in range(30):
        level = generate_level(level_num, random.Random(seed))
        distances = get_bfs_distances(level.maze, level.players[1].pos)
        path = get_shortest_path(level.maze, level.players[1].pos, level.exit)
        hunters, wanderers, bonuses, _ = constants.LEVEL_CONTENTS[level_num]
        symbols = [symbol for symbol, cell in level.monsters]
        assert symbols.count(constants.HUNTER) == hunters
        assert symbols.count(constants.WANDERER) == wanderers
        assert len(level.bonuses) == bonuses
        positions = [level.players[1].pos, level.exit, level.key]
        for symbol, cell in level.monsters:
            assert distances[cell] >= constants.MONSTER_MIN_SPAWN_DISTANCE
            assert cell not in path
            positions.append(cell)
        for cell, symbol in level.bonuses.items():
            assert symbol in (constants.FREEZE, constants.TORCH,
                              constants.COMPASS)
            positions.append(cell)
        assert len(positions) == len(set(positions))
        for cell in positions:
            assert cell in distances
            assert level.maze[cell.row][cell.col] == constants.FILE_AIR


def test_objects_seed_and_unchanged_map():
    """Seed повторяет весь уровень; расстановка не меняет карту."""
    first = generate_level(0, random.Random(2))
    assert first == generate_level(0, random.Random(2))
    before = [row[:] for row in first.maze]
    level = Level(
        maze=first.maze,
        exit=first.exit,
        key=None,
        players={1: Player(
            nick=None,
            pos=first.players[1].pos,
            last_played_round=None)
        })
    result = place_objects(level, 0, random.Random(5))
    assert result is level
    assert result.maze is first.maze
    assert first.maze == before


def test_objects_not_enough_monster_cells():
    """На единственном пути к выходу монстра ставить нельзя."""
    maze = [list(row) for row in [
        '###########', '#.........#', '###########',
        '###########', '###########',
    ]]
    before = [row[:] for row in maze]
    level = Level(
        maze=maze,
        exit=Cell(1, 9),
        key=None,
        players={1: Player(
            nick=None,
            pos=Cell(1, 1),
            last_played_round=None)
        })
    with pytest.raises(PlaceError, match='для монстров'):
        place_objects(level, 0, random.Random(0))
    assert maze == before


def test_bonus_behind_monster(monkeypatch):
    """Бонус доступен через клетку монстра; дистанция ровно 7 допустима."""
    maze = [list(row) for row in [
        '###########', '#.........#', '#########.#',
        '#########.#', '###########',
    ]]
    monkeypatch.setattr(constants, 'LEVEL_CONTENTS', [(1, 0, 7, 0)])
    # До клетки (1, 8) ровно 7 шагов, она уже подходит для монстра.
    monkeypatch.setattr(constants, 'MONSTER_MIN_SPAWN_DISTANCE', 7)
    level = Level(
        maze=maze,
        exit=Cell(1, 3),
        key=None,
        players={1: Player(
            nick=None,
            pos=Cell(1, 1),
            last_played_round=None)
        })
    place_objects(level, 0, random.Random(1))
    assert level.monsters == [(constants.HUNTER, Cell(1, 8))]
    assert len(level.bonuses) == 7
    assert Cell(3, 9) in level.bonuses


@pytest.mark.parametrize('level_num', [-1, constants.MAX_LEVEL + 1,
                                       True, '0', 0.5])
def test_objects_invalid_level(level_num):
    """Неверный номер не используется как индекс настроек."""
    with pytest.raises(PlaceError, match='номер уровня'):
        place_objects(Level(
            maze=[],
            exit=Cell(3, 3),
            key=None,
            players={1: Player(
                nick=None,
                pos=Cell(1, 1),
                last_played_round=None)
            }), level_num)
    with pytest.raises(GenerationError):
        generate_level(level_num)


def test_objects_invalid_map_and_positions():
    """Ошибки карты и совпадение старта с выходом отклоняются."""
    with pytest.raises(LevelError):
        place_objects(Level(
            maze=[],
            exit=Cell(3, 3),
            key=None,
            players={1: Player(
                nick=None,
                pos=Cell(1, 1),
                last_played_round=None)
            }), 0)
    level = generate_level(0, random.Random(2))
    empty = Level(
        maze=level.maze,
        exit=level.players[1].pos,
        key=None,
        players={1: Player(
            nick=None,
            pos=level.players[1].pos,
            last_played_round=None)
        })
    message = 'Координаты выхода и игрока совпадают'
    with pytest.raises(LevelError, match=message):
        place_objects(empty, 0)


def test_objects_requires_level():
    """Расстановка принимает только объект Level."""
    with pytest.raises(LevelError, match='объект Level'):
        place_objects(None, 0)


def test_objects_rejects_filled_level():
    """Повторная расстановка не меняет уже заполненный уровень."""
    level = generate_level(0, random.Random(2))
    expected = generate_level(0, random.Random(2))
    with pytest.raises(PlaceError, match='уже содержит'):
        place_objects(level, 0)
    assert level == expected


def test_objects_unreachable_air(monkeypatch):
    """Изолированный проход не подходит для ключа или бонуса."""
    maze = [list(row) for row in [
        '#######', '#...#.#', '#######', '#.#####', '#######',
    ]]
    monkeypatch.setattr(constants, 'LEVEL_CONTENTS', [(0, 0, 0, 0)])
    level = Level(
        maze=maze,
        exit=Cell(1, 3),
        key=None,
        players={1: Player(
            nick=None,
            pos=Cell(1, 1),
            last_played_round=None)
        })
    place_objects(level, 0)
    assert level.key == Cell(1, 2)
    monkeypatch.setattr(constants, 'LEVEL_CONTENTS', [(0, 0, 1, 0)])
    with pytest.raises(PlaceError, match='для всех объектов'):
        place_objects(Level(
            maze=maze,
            exit=Cell(1, 3),
            key=None,
            players={1: Player(
                nick=None,
                pos=Cell(1, 1),
                last_played_round=None)
            }), 0)


def test_key_can_be_reached_through_exit(monkeypatch):
    """Выход не считается стеной при поиске доступного места ключа."""
    maze = [list(row) for row in [
        '#####', '#...#', '#####', '#####', '#####',
    ]]
    monkeypatch.setattr(constants, 'LEVEL_CONTENTS', [(0, 0, 0, 0)])
    level = Level(
        maze=maze,
        exit=Cell(1, 2),
        key=None,
        players={1: Player(
            nick=None,
            pos=Cell(1, 1),
            last_played_round=None)
        })
    place_objects(level, 0)
    assert level.key == Cell(1, 3)
    assert level.maze[1][2] == constants.FILE_AIR


def test_key_preserves_only_monster_cell(monkeypatch):
    """Ключ не занимает единственное место с нужной дистанцией."""
    maze = [list(row) for row in [
        '###########', '#.........#', '#.#########',
        '#.#########', '###########',
    ]]
    monkeypatch.setattr(constants, 'LEVEL_CONTENTS', [(1, 0, 0, 0)])
    monkeypatch.setattr(constants, 'MONSTER_MIN_SPAWN_DISTANCE', 8)
    level = Level(
        maze=maze,
        exit=Cell(3, 1),
        key=None,
        players={1: Player(
            nick=None,
            pos=Cell(1, 1),
            last_played_round=None)
        })
    place_objects(level, 0, random.Random(0))
    assert level.monsters == [(constants.HUNTER, Cell(1, 9))]
    assert level.key != Cell(1, 9)


@pytest.mark.parametrize('level_num', range(2, constants.MAX_LEVEL))
def test_objects_with_two_players(level_num):
    """Монстры далеко от каждого игрока и вне путей каждого к выходу."""
    for seed in range(20):
        base = generate_level(level_num, random.Random(seed))
        first = base.players[1].pos
        cells = get_bfs_distances(base.maze, first)
        second = random.Random(seed).choice(
            [cell for cell in cells if cell not in (first, base.exit)])
        level = Level(maze=base.maze, exit=base.exit, key=None,
                      players={1: Player(pos=first), 2: Player(pos=second)})
        place_objects(level, level_num, random.Random(seed))
        for position in (first, second):
            distances = get_bfs_distances(level.maze, position)
            path = get_shortest_path(level.maze, position, level.exit)
            for symbol, cell in level.monsters:
                assert distances[cell] >= constants.MONSTER_MIN_SPAWN_DISTANCE
                assert cell not in path

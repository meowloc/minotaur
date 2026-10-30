"""Прямые проверки результата трёх функций генерации."""

import random

import pytest

from minotaur import constants
from minotaur.custom_types import Cell
from minotaur.exceptions import GenerationError, LevelError, PlaceError
from minotaur.generator import add_loops, init_map_gen, making_labyrinth
from minotaur.levels import place_exit_and_player
from minotaur.pathfinding import get_bfs_distances


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


def test_generation_to_level_file(tmp_path):
    """Карта и координаты проходят все этапы без поиска объектов в матрице."""
    from minotaur.custom_types import Level
    from minotaur.levels import load_level, save_level, validate_level

    rng = random.Random(2)
    maze = init_map_gen(0)
    player, exit_pos = place_exit_and_player(maze, rng)
    making_labyrinth(maze, player, exit_pos, rng)
    add_loops(maze, constants.LEVEL_CONTENTS[0][3], rng)
    for row in maze:
        for symbol in row:
            assert symbol in (constants.FILE_AIR, constants.FILE_WALL)
    level = Level(maze, player, exit_pos, None)
    validate_level(level)
    path = tmp_path / 'generated.json'
    save_level(level, path)
    assert load_level(path) == level


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

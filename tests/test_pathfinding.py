import pytest

from minotaur import pathfinding
from minotaur.custom_types import Cell
from minotaur.exceptions import LevelError

mock_maze_2_rows_2_cols = [
    list("##"),
    list("##"),
]

mock_maze_5_rows_5_cols = [
    list("#####"),
    list("##..#"),
    list("##.##"),
    list("#..##"),
    list("#####"),
]

mock_maze_2_areas = [
    list("#####"),
    list("#.#.#"),
    list("#####"),
    list("#####"),
    list("#####"),
]

mock_maze_bad_symbol = [
    list("#@###"),
    list("#.###"),
    list("#####"),
    list("#####"),
    list("#####"),
]

mock_maze_bad_length = [
    list("#####"),
    list("###"),
    list("#"),
    list("###"),
    list("#####"),
]


def test_validate_data_is_correct():
    """Правильный лабиринт и клетка проходят проверку без ошибки."""
    pathfinding.validate_input(mock_maze_5_rows_5_cols, Cell(1, 2))


@pytest.mark.parametrize("maze, cell, message", [
    (None, Cell(1, 1), "Maze and cell must be specified!"),
    (mock_maze_5_rows_5_cols, None, "Maze and cell must be specified!"),
    (mock_maze_2_rows_2_cols, Cell(1, 1), "Maze has incorrect size!"),
    (mock_maze_bad_symbol, Cell(1, 1), "Maze has incorrect symbol @!"),
    (mock_maze_bad_length, Cell(1, 1),
     "Maze has incorrect length! Found: 3. Was expecting: 5"),
    (mock_maze_5_rows_5_cols, Cell(0, 0), "isn't correct coordinates"),
    (mock_maze_5_rows_5_cols, Cell(1, 1), "isn't correct coordinates"),
])
def test_validate_incorrect_data(maze, cell, message):
    """Пустые данные, лабиринт меньше 5x5, посторонний символ, строки
    разной длины, клетка на рамке или в стене вызывают ошибку."""
    with pytest.raises(LevelError, match=message):
        pathfinding.validate_input(maze, cell)


@pytest.mark.parametrize("maze, cell, expected", [
    (mock_maze_5_rows_5_cols, Cell(1, 2), [Cell(2, 2), Cell(1, 3)]),
    (mock_maze_5_rows_5_cols, Cell(1, 3), [Cell(1, 2)]),
    (mock_maze_2_areas, Cell(1, 1), []),
])
def test_get_neighbors(maze, cell, expected):
    """На повороте два соседа, в тупике один, у изолированной клетки нет."""
    assert pathfinding.get_neighbors(maze, cell) == expected


def test_get_neighbors_wall_cell():
    """Запрос соседей для стены вызывает ошибку."""
    with pytest.raises(LevelError):
        pathfinding.get_neighbors(mock_maze_5_rows_5_cols, Cell(1, 1))


@pytest.mark.parametrize("maze, start, expected", [
    (mock_maze_5_rows_5_cols, Cell(1, 3), {
        Cell(1, 3): 0, Cell(1, 2): 1, Cell(2, 2): 2,
        Cell(3, 2): 3, Cell(3, 1): 4,
    }),
    (mock_maze_2_areas, Cell(1, 1), {Cell(1, 1): 0}),
])
def test_get_bfs_distances(maze, start, expected):
    """Расстояния считаются только до достижимых клеток."""
    assert pathfinding.get_bfs_distances(maze, start) == expected


def test_get_bfs_distances_start_outside():
    """Старт на рамке вызывает ошибку."""
    with pytest.raises(LevelError):
        pathfinding.get_bfs_distances(mock_maze_5_rows_5_cols, Cell(0, 2))


@pytest.mark.parametrize("goal, length, expected", [
    (Cell(3, 1), None, [Cell(1, 2), Cell(2, 2), Cell(3, 2), Cell(3, 1)]),
    (Cell(3, 1), 2, [Cell(1, 2), Cell(2, 2)]),
    (Cell(2, 2), 8, [Cell(1, 2), Cell(2, 2)]),
    (Cell(1, 3), None, []),
])
def test_get_shortest_path(goal, length, expected):
    """Путь не включает старт, обрезается до length; путь в ту же
    клетку пуст."""
    result = pathfinding.get_shortest_path(
        mock_maze_5_rows_5_cols, Cell(1, 3), goal, length)
    assert result == expected


@pytest.mark.parametrize("maze, start, goal, length", [
    (mock_maze_5_rows_5_cols, Cell(1, 2), Cell(1, 1), None),
    (mock_maze_5_rows_5_cols, Cell(0, 0), Cell(3, 1), None),
    (mock_maze_2_areas, Cell(1, 1), Cell(1, 3), None),
    (mock_maze_5_rows_5_cols, Cell(1, 3), Cell(3, 1), 0),
])
def test_get_shortest_path_errors(maze, start, goal, length):
    """Цель в стене, старт на рамке, недостижимая цель или длина
    меньше 1 вызывают ошибку."""
    with pytest.raises(LevelError):
        pathfinding.get_shortest_path(maze, start, goal, length)

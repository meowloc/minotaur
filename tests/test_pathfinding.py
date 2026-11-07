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


@pytest.mark.parametrize("maze, message", [
    (None, "Maze and cell must be specified!"),
    (mock_maze_2_rows_2_cols, "Maze has incorrect size!"),
    (mock_maze_bad_symbol, "Maze has incorrect symbol @!"),
    (mock_maze_bad_length,
     "Maze has incorrect length! Found: 3. Was expecting: 5"),
])
def test_validate_incorrect_maze(maze, message):
    """Отсутствие лабиринта, размер меньше 5x5, посторонний символ
    или строки разной длины вызывают ошибку."""
    with pytest.raises(LevelError, match=message):
        pathfinding.validate_input(maze, Cell(1, 1))


@pytest.mark.parametrize("cell, message", [
    (None, "Maze and cell must be specified!"),
    (Cell(0, 0), "isn't correct coordinates"),
    (Cell(1, 1), "isn't correct coordinates"),
])
def test_validate_incorrect_cell(cell, message):
    """Отсутствие клетки, клетка на рамке или в стене вызывают ошибку."""
    with pytest.raises(LevelError, match=message):
        pathfinding.validate_input(mock_maze_5_rows_5_cols, cell)


@pytest.mark.parametrize("maze, cell, expected", [
    (mock_maze_5_rows_5_cols, Cell(1, 2), [Cell(2, 2), Cell(1, 3)]),
    (mock_maze_5_rows_5_cols, Cell(1, 3), [Cell(1, 2)]),
    (mock_maze_2_areas, Cell(1, 1), []),
])
def test_get_neighbors(maze, cell, expected):
    """На повороте два соседа, в тупике один, у изолированной клетки нет."""
    assert pathfinding.get_neighbors(maze, cell) == expected


@pytest.mark.parametrize("maze, cell, message", [
    ([], Cell(1, 1), "Maze and cell must be specified!"),
    (mock_maze_5_rows_5_cols, Cell(0, 2), "incorrect!"),
    (mock_maze_5_rows_5_cols, Cell(1, 1), "is a wall!"),
])
def test_get_neighbors_errors(maze, cell, message):
    """Пустой лабиринт, клетка на рамке или стена вызывают ошибку."""
    with pytest.raises(LevelError, match=message):
        pathfinding.get_neighbors(maze, cell)


def test_get_bfs_distances():
    """Расстояния считаются до всех достижимых клеток."""
    result = pathfinding.get_bfs_distances(mock_maze_5_rows_5_cols,
                                           Cell(1, 3))
    assert result == {
        Cell(1, 3): 0, Cell(1, 2): 1, Cell(2, 2): 2,
        Cell(3, 2): 3, Cell(3, 1): 4,
    }


def test_get_bfs_distances_unreachable():
    """Недостижимая клетка не попадает в результат."""
    result = pathfinding.get_bfs_distances(mock_maze_2_areas, Cell(1, 1))
    assert result == {Cell(1, 1): 0}


def test_get_bfs_distances_start_outside():
    """Старт на рамке вызывает ошибку."""
    with pytest.raises(LevelError):
        pathfinding.get_bfs_distances(mock_maze_5_rows_5_cols, Cell(0, 2))


@pytest.mark.parametrize("goal, expected", [
    (Cell(3, 1), [Cell(1, 2), Cell(2, 2), Cell(3, 2), Cell(3, 1)]),
    (Cell(1, 3), []),
])
def test_get_shortest_path(goal, expected):
    """Путь не включает старт; путь в ту же клетку пуст."""
    result = pathfinding.get_shortest_path(
        mock_maze_5_rows_5_cols, Cell(1, 3), goal)
    assert result == expected


@pytest.mark.parametrize("goal, length, expected", [
    (Cell(3, 1), 2, [Cell(1, 2), Cell(2, 2)]),
    (Cell(2, 2), 8, [Cell(1, 2), Cell(2, 2)]),
])
def test_get_shortest_path_with_length(goal, length, expected):
    """Путь обрезается до length; если путь короче, он возвращается
    целиком."""
    result = pathfinding.get_shortest_path(
        mock_maze_5_rows_5_cols, Cell(1, 3), goal, length)
    assert result == expected


@pytest.mark.parametrize("start, goal, length", [
    (Cell(1, 2), Cell(1, 1), None),
    (Cell(0, 0), Cell(3, 1), None),
    (Cell(1, 3), Cell(3, 1), 0),
])
def test_get_shortest_path_errors(start, goal, length):
    """Цель в стене, старт на рамке или длина меньше 1 вызывают ошибку."""
    with pytest.raises(LevelError):
        pathfinding.get_shortest_path(
            mock_maze_5_rows_5_cols, start, goal, length)


def test_get_shortest_path_unreachable():
    """Недостижимая цель вызывает ошибку."""
    with pytest.raises(LevelError, match="is unreachable from"):
        pathfinding.get_shortest_path(mock_maze_2_areas,
                                      Cell(1, 1), Cell(1, 3))

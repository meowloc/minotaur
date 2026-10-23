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


def test_validate_no_maze():
    """Отсутствие лабиринта вызывает ошибку."""
    with pytest.raises(LevelError, match="Maze and cell must be specified!"):
        pathfinding.validate_input(None, Cell(1, 1))


def test_validate_no_cell():
    """Отсутствие координаты клетки вызывает ошибку."""
    with pytest.raises(LevelError, match="Maze and cell must be specified!"):
        pathfinding.validate_input(mock_maze_5_rows_5_cols, None)


def test_validate_no_maze_and_cell():
    """Отсутствие и лабиринта, и клетки вызывает ошибку."""
    with pytest.raises(LevelError, match="Maze and cell must be specified!"):
        pathfinding.validate_input(None, None)


def test_validate_incorrect_sized_maze():
    """Лабиринт меньше 3×3 вызывает ошибку."""
    with pytest.raises(LevelError,
                       match="Maze has incorrect size!"):
        pathfinding.validate_input(mock_maze_2_rows_2_cols, Cell(1, 1))


def test_validate_maze_contains_incorrect_symbol():
    """Посторонний символ в лабиринте вызывает ошибку."""
    with pytest.raises(LevelError, match="Maze has incorrect symbol @!"):
        pathfinding.validate_input([
            list("#@###"),
            list("#.###"),
            list("#####"),
            list("#####"),
            list("#####"),
        ], Cell(1, 1))


def test_validate_incorrect_maze():
    """Строки разной длины вызывают ошибку."""
    with pytest.raises(
            LevelError,
            match="Maze has incorrect length! Found: 3. Was expecting: 5"
    ):
        pathfinding.validate_input([
            list("#####"),
            list("###"),
            list("#"),
            list("###"),
            list("#####"),
        ], Cell(1, 1))


def test_validate_cell_outside_range():
    """Клетка на рамке лабиринта вызывает ошибку."""
    with pytest.raises(LevelError, match="isn't correct coordinates"):
        pathfinding.validate_input(mock_maze_5_rows_5_cols, Cell(0, 0))


def test_validate_cell_is_wall():
    """Клетка со стеной вызывает ошибку."""
    with pytest.raises(LevelError, match="isn't correct coordinates"):
        pathfinding.validate_input(mock_maze_5_rows_5_cols, Cell(1, 1))


def test_validate_data_is_correct():
    """Правильный лабиринт и клетка проходят проверку без ошибки."""
    pathfinding.validate_input(mock_maze_5_rows_5_cols, Cell(1, 2))


def test_get_neighbors_in_corridor():
    """У клетки на повороте коридора два соседа."""
    result = pathfinding.get_neighbors(mock_maze_5_rows_5_cols, Cell(1, 2))
    assert result == [Cell(2, 2), Cell(1, 3)]


def test_get_neighbors_in_dead_end():
    """У клетки в тупике один сосед."""
    result = pathfinding.get_neighbors(mock_maze_5_rows_5_cols, Cell(1, 3))
    assert result == [Cell(1, 2)]


def test_get_neighbors_isolated_cell():
    """У клетки, окружённой стенами, соседей нет."""
    result = pathfinding.get_neighbors(mock_maze_2_areas, Cell(1, 1))
    assert result == []


def test_get_neighbors_wall_cell():
    """Запрос соседей для стены вызывает ошибку."""
    with pytest.raises(LevelError):
        pathfinding.get_neighbors(mock_maze_5_rows_5_cols, Cell(1, 1))


def test_get_bfs_distances():
    """Расстояния считаются до всех достижимых клеток."""
    result = pathfinding.get_bfs_distances(mock_maze_5_rows_5_cols,
                                           Cell(1, 3))
    assert result == {
        Cell(1, 3): 0,
        Cell(1, 2): 1,
        Cell(2, 2): 2,
        Cell(3, 2): 3,
        Cell(3, 1): 4,
    }


def test_get_bfs_distances_unreachable():
    """Недостижимая клетка не попадает в результат."""
    result = pathfinding.get_bfs_distances(mock_maze_2_areas, Cell(1, 1))
    assert result == {Cell(1, 1): 0}
    assert Cell(1, 3) not in result


def test_get_bfs_distances_start_outside():
    """Старт на рамке вызывает ошибку."""
    with pytest.raises(LevelError):
        pathfinding.get_bfs_distances(mock_maze_5_rows_5_cols, Cell(0, 2))


def test_get_shortest_path():
    """Путь идёт от старта до цели по кратчайшему маршруту."""
    result = pathfinding.get_shortest_path(mock_maze_5_rows_5_cols,
                                           Cell(1, 3), Cell(3, 1))
    assert result == [Cell(1, 2), Cell(2, 2),
                      Cell(3, 2), Cell(3, 1)]


def test_get_shortest_path_same_cell():
    """Путь из клетки в неё же состоит из одной клетки."""
    result = pathfinding.get_shortest_path(mock_maze_5_rows_5_cols,
                                           Cell(2, 2), Cell(2, 2))
    assert result == []


def test_get_shortest_path_goal_is_wall():
    """Клетка в стене вызывает ошибку."""
    with pytest.raises(LevelError):
        pathfinding.get_shortest_path(mock_maze_5_rows_5_cols,
                                      Cell(1, 2), Cell(1, 1))


def test_get_shortest_path_with_length():
    """Возвращает только первые клетки пути."""
    result = pathfinding.get_shortest_path(
        mock_maze_5_rows_5_cols, Cell(1, 3), Cell(3, 1), 2
    )
    assert result == [Cell(1, 2), Cell(2, 2)]


def test_get_shortest_path_length_longer_than_path():
    """Если путь короче длины, возвращается весь путь."""
    result = pathfinding.get_shortest_path(
        mock_maze_5_rows_5_cols, Cell(1, 3), Cell(2, 2), 8
    )
    assert result == [Cell(1, 2), Cell(2, 2)]


def test_get_shortest_path_start_on_border():
    """Старт на рамке вызывает ошибку."""
    with pytest.raises(LevelError):
        pathfinding.get_shortest_path(
            mock_maze_5_rows_5_cols, Cell(0, 0), Cell(3, 1), 8
        )


def test_get_shortest_path_unreachable():
    """Недостижимая цель вызывает ошибку."""
    with pytest.raises(LevelError, match="is unreachable from"):
        pathfinding.get_shortest_path(mock_maze_2_areas,
                                      Cell(1, 1), Cell(1, 3))

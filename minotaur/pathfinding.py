from collections import deque
from minotaur.exceptions import LevelError
from minotaur.custom_types import Maze, Cell

import minotaur.constants as constants


def validate_input(maze: Maze, cell: Cell) -> None:
    """Проверяет, что лабиринт и клетка подходят для поиска пути.

    Args:
        maze: Карта лабиринта: список строк из символов стен и проходов.
        cell: Координата клетки, которую нужно проверить.

    Raises:
        LevelError: Если лабиринт пустой, меньше 5×5, содержит строки
            разной длины или посторонние символы, если по координатам
            расположена стена, а также если cell не является Cell или
            лежит на рамке или за пределами лабиринта.
    """
    if not maze or not isinstance(cell, Cell):
        raise LevelError("Maze and cell must be specified!")

    height, width = len(maze), len(maze[0])

    if height < 5 or width < 5:
        raise LevelError("Maze has incorrect size!")

    for row in maze:
        for item in row:
            if item not in (constants.FILE_WALL, constants.FILE_AIR):
                raise LevelError(f"Maze has incorrect symbol {item}!")
        if len(row) != len(maze[0]):
            raise LevelError(
                "Maze has incorrect length! "
                f"Found: {len(row)}. Was expecting: {width}"
            )

    if (not (1 <= cell.row <= height - 2 and 1 <= cell.col <= width - 2)
            or maze[cell.row][cell.col] == constants.FILE_WALL):
        raise LevelError(f"{cell} isn't correct coordinates!")


def get_neighbors(maze: Maze, cell: Cell) -> list[Cell]:
    """Возвращает проходимые клетки, соседние с заданной.

    Args:
        maze: Двумерная сетка тайлов, индексируется как ``maze[row][col]``.
        cell: Клетка, соседей которой нужно найти.

    Returns:
        Список координат соседних клеток, которые являются проходами.
        Порядок соответствует порядку направлений в
        ``constants.DIRECTIONS``. Если вокруг только стены, список пуст.

    Raises:
        LevelError: Если лабиринт пустой или ``cell`` лежит на рамке
            или за пределами лабиринта, либо если клетка стена.
    """
    if len(maze) == 0 or len(maze[0]) == 0:
        raise LevelError("Maze and cell must be specified!")

    if not (0 < cell.row < (len(maze) - 1)
            and 0 < cell.col < (len(maze[0]) - 1)):
        raise LevelError(f"{cell} incorrect!")

    if maze[cell.row][cell.col] == constants.FILE_WALL:
        raise LevelError(f"{cell} is a wall!")

    neighbors = []
    for d_row, d_col in constants.DIRECTIONS.values():
        new_row, new_col = cell.row + d_row, cell.col + d_col
        if maze[new_row][new_col] == constants.FILE_AIR:
            neighbors.append(Cell(new_row, new_col))

    return neighbors


def get_bfs_distances(maze: Maze, start: Cell) -> dict[Cell, int]:
    """Вычисляет кратчайшие расстояния от стартовой клетки до всех достижимых.

    Args:
        maze: Двумерная сетка тайлов, индексируется как ``maze[row][col]``.
        start: Клетка, от которой считаются расстояния.

    Returns:
        Словарь, сопоставляющий каждой достижимой клетке минимальное
        число шагов от ``start``. Сама ``start`` входит в словарь с
        расстоянием 0, недостижимые клетки в него не попадают.

    Raises:
        LevelError: Если лабиринт или ``start`` не прошли проверку
            ``validate_input``.
    """
    validate_input(maze, start)

    distances = {start: 0}
    queue = deque([start])
    while queue:
        curr_cell = queue.popleft()
        for next_cell in get_neighbors(maze, curr_cell):
            if next_cell not in distances:
                distances[next_cell] = distances[curr_cell] + 1
                queue.append(next_cell)

    return distances


def get_shortest_path(
        maze: Maze, start: Cell, goal: Cell, length: int | None = None
) -> list[Cell]:
    """Находит кратчайший путь от стартовой клетки до заданной.

    Args:
        maze: Двумерная сетка тайлов, индексируется как ``maze[row][col]``.
        start: Клетка, из которой начинается путь.
        goal: Клетка, в которую нужно прийти.
        length: Сколько первых шагов пути вернуть. Если не указано,
            возвращается весь путь.

    Returns:
        Список клеток кратчайшего пути по порядку, начиная с первого
        шага после ``start`` и до ``goal`` включительно. Сама ``start``
        в путь не входит. С ``length`` путь обрезается до первых
        ``length`` шагов. Если ``start`` и ``goal`` совпадают, список
        пуст.

    Raises:
        LevelError: Если лабиринт, ``start`` или ``goal`` не прошли
            проверку ``validate_input``, ``goal`` недостижима из
            ``start`` или ``length`` меньше 1.
    """
    validate_input(maze, start)
    validate_input(maze, goal)

    paths = {start: [start]}
    queue = deque([start])
    while queue:
        curr_cell = queue.popleft()
        for next_cell in get_neighbors(maze, curr_cell):
            if next_cell not in paths:
                path = paths[curr_cell] + [next_cell]
                paths[next_cell] = path
                queue.append(next_cell)

    if goal not in paths:
        raise LevelError(f"{goal} is unreachable from {start}!")

    if length is not None and length < 1:
        raise LevelError("Length must be positive!")

    path = paths[goal][1:]

    return path[:length]

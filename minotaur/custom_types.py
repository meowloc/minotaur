from typing import NamedTuple

Maze = list[list[str]]


class Cell(NamedTuple):
    """Координата клетки лабиринта.

    Attributes:
        row: Номер строки, начиная сверху.
        col: Номер столбца, начиная слева.
    """

    row: int
    col: int

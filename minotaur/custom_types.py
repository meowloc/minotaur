from dataclasses import dataclass, field
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


@dataclass
class Level:
    """Уровень: карта и расположение объектов на ней.

    Attributes:
        maze: Карта из стен и проходов, без объектов.
        player: Позиция игрока.
        exit: Позиция выхода.
        key: Позиция ключа, ``None``, если ключ уже подобран.
        monsters: Монстры в виде пар из символа монстра и его позиции.
        bonuses: Бонусы: позиция бонуса и его символ.
        freeze_turns: Сколько ходов ещё действует заморозка, 0 — не действует.
        torch_active: Действует ли факел до конца уровня.
    """

    maze: Maze
    player: Cell
    exit: Cell
    key: Cell | None
    monsters: list[tuple[str, Cell]] = field(default_factory=list)
    bonuses: dict[Cell, str] = field(default_factory=dict)
    freeze_turns: int = 0
    torch_active: bool = False

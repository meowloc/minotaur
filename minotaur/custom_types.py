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
class Player:
    """Класс игрока, используемый в классе Level.

    Attributes:
        id: Уникальный идентификатор игрока.
        nick: Никнейм игрока, ``None``, если не задан.
        pos: Текущая позиция игрока в лабиринте.
        last_played_round: Номер последнего раунда, в котором
            игрок участвовал. ``None``, если ещё не участвовал.
        is_connected: Подключён ли игрок к серверу.
        is_alive: Жив ли игрок.
        is_ready: Готов ли игрок к началу раунда.
        torch_active: Действует ли факел у конкретного игрока
            до конца уровня.
        steps: Количество совершённых игроком шагов.
        score: Количество набранных игроком очков.
    """

    id: int
    nick: str | None
    pos: Cell

    last_played_round: int | None
    is_connected: bool = False
    is_alive: bool = True
    is_ready: bool = False

    torch_active: bool = False

    steps: int = 0
    score: int = 0


@dataclass
class Level:
    """Уровень: карта и расположение объектов на ней.

    Attributes:
        maze: Карта из стен и проходов, без объектов.
        players: Словарь, вида id: Player.
        exit: Позиция выхода.
        key: Позиция ключа, ``None``, если ключ уже подобран.
        monsters: Монстры в виде пар из символа монстра и его позиции.
        bonuses: Бонусы: позиция бонуса и его символ.
        freeze_turns: Сколько ходов ещё действует заморозка, 0 — не действует.
    """

    maze: Maze
    exit: Cell
    key: Cell | None

    players: dict[int, Player] = field(default_factory=dict)
    monsters: list[tuple[str, Cell]] = field(default_factory=list)
    bonuses: dict[Cell, str] = field(default_factory=dict)
    freeze_turns: int = 0

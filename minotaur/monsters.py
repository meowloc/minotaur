import random
from dataclasses import dataclass
from typing import ClassVar

from minotaur import constants
from minotaur.custom_types import Cell, Maze
from minotaur.pathfinding import get_neighbors, get_shortest_path


@dataclass
class Monster:
    """Базовый класс монстра.

    Attributes:
        position: Клетка, на которой стоит монстр.
    """

    symbol: ClassVar[str]
    position: Cell

    def step(self, maze: Maze, player: Cell, turn: int,
             rng: random.Random) -> None:
        """Делает один ход монстра, меняя ``position``.

        Args:
            maze: Карта лабиринта.
            player: Позиция игрока.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел.

        Raises:
            NotImplementedError: Всегда, метод переопределяется
                в наследниках.
        """
        raise NotImplementedError


@dataclass
class Hunter(Monster):
    """Монстр, который идёт к игроку по кратчайшему пути."""

    symbol: ClassVar[str] = constants.HUNTER

    def step(self, maze: Maze, player: Cell, turn: int,
             rng: random.Random) -> None:
        """Делает шаг к игроку раз в ``HUNTER_STEP_RATE`` ходов.

        Если охотник уже стоит на клетке игрока, он остаётся на месте.

        Args:
            maze: Карта лабиринта.
            player: Позиция игрока.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел, охотником не используется.

        Raises:
            LevelError: Если позиция охотника или игрока некорректна,
                или игрок недостижим (из ``get_shortest_path``).
        """
        if turn % constants.HUNTER_STEP_RATE != 0:
            return
        path = get_shortest_path(maze, self.position, player)
        if path:
            self.position = path[0]


@dataclass
class Wanderer(Monster):
    """Монстр, который бродит и преследует игрока вблизи.

    Attributes:
        previous: Клетка, с которой бродяга пришёл, или ``None``.
        visibility_range: Расстояние до игрока в шагах, в пределах
            которого бродяга начинает погоню.
    """

    symbol: ClassVar[str] = constants.WANDERER
    previous: Cell | None = None
    visibility_range: int = constants.WANDERER_CHASE_BFS_STEPS

    def step(self, maze: Maze, player: Cell, turn: int,
             rng: random.Random) -> None:
        """Гонится за близким игроком, иначе делает случайный шаг.

        Случайный шаг не ведёт назад, если только бродяга не в тупике.

        Args:
            maze: Карта лабиринта.
            player: Позиция игрока.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел для выбора направления.

        Raises:
            LevelError: Если позиция бродяги или игрока некорректна,
                или игрок недостижим (из ``get_shortest_path``).
        """
        if turn % constants.WANDERER_STEP_RATE != 0:
            return
        path = get_shortest_path(maze, self.position, player)
        if len(path) <= self.visibility_range:
            next_cell = path[0] if path else self.position
        else:
            neighbors = get_neighbors(maze, self.position)
            forward = [cell for cell in neighbors if cell != self.previous]
            next_cell = rng.choice(forward or neighbors)

        self.previous = self.position
        self.position = next_cell
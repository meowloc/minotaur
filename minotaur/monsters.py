
import random
from dataclasses import dataclass
from typing import ClassVar

from minotaur import constants
from minotaur.custom_types import Cell, Maze, Player
from minotaur.exceptions import LevelError
from minotaur.pathfinding import get_neighbors, get_shortest_path


@dataclass
class Monster:
    """Базовый класс монстра.

    Attributes:
        symbol: Символ, которым монстр обозначен на карте.
        position: Клетка, на которой стоит монстр.
        step_rate: Частота хода конкретного монстра.
        turns_until_move: Количество ходов, оставшихся до хода монстра.
    """

    symbol: ClassVar[str]
    position: Cell
    step_rate: ClassVar[int]
    turns_until_move: int = 0

    def tick(self, maze: Maze, players: dict[int, Player], turn: int,
             rng: random.Random, is_freeze_active: bool) -> None:
        """Делает один ход монстра, меняя ``position``.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел.
            is_freeze_active: Активен ли бонус (заморозка).
        """
        if is_freeze_active:
            return

        if self.turns_until_move > 1:
            self.turns_until_move -= 1
        else:
            self.turns_until_move = self.step_rate
            self._step(maze, players, turn, rng)

    def _get_nearest_player(
            self, maze: Maze, players: dict[int, Player]
    ) -> tuple[Player, list[Cell] | None] | None:
        """Находит ближайшего живого игрока по кратчайшему пути.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.

        Returns:
            Ближайший игрок и кратчайший путь до него или ``None``,
            если доступных игроков нет.
        """
        nearest, shortest_path = None, None

        for player in players.values():
            if not player.is_alive:
                continue

            try:
                path = get_shortest_path(maze, self.position, player.pos)
            except LevelError:
                continue

            if shortest_path is None or len(path) < len(shortest_path):
                nearest = player
                shortest_path = path

        if nearest is None:
            return None

        return nearest, shortest_path

    def _step(self, maze: Maze, players: dict[int, Player], turn: int,
              rng: random.Random) -> None:
        """Делает один ход монстра, меняя ``position``.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел.

        Raises:
            NotImplementedError: Всегда, метод переопределяется
                в наследниках.
        """
        raise NotImplementedError


@dataclass
class Hunter(Monster):
    """Монстр, который идёт к ближайшему игроку по кратчайшему пути."""

    symbol: ClassVar[str] = constants.HUNTER
    step_rate: ClassVar[int] = constants.HUNTER_STEP_RATE
    turns_until_move: int = 0

    def _step(self, maze: Maze, players: dict[int, Player], turn: int,
              rng: random.Random) -> None:
        """Делает шаг к ближайшему игроку раз в ``HUNTER_STEP_RATE`` ходов.

        Если охотник уже стоит на клетке игрока, он остаётся на месте.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел, охотником не используется.

        Raises:
            LevelError: Если позиция охотника или игрока некорректна,
                или игрок недостижим (из ``get_shortest_path``).
        """
        target = self._get_nearest_player(maze, players)

        if target is None:
            return

        _, path = target

        if path:
            self.position = path[0]


@dataclass
class Wanderer(Monster):
    """Монстр, который бродит и преследует ближайшего игрока.

    Attributes:
        previous: Клетка, с которой бродяга пришёл, или ``None``.
        visibility_range: Расстояние до игрока в шагах, в пределах
            которого бродяга начинает погоню.
    """

    symbol: ClassVar[str] = constants.WANDERER
    step_rate: ClassVar[int] = constants.WANDERER_STEP_RATE
    turns_until_move: int = 0
    previous: Cell | None = None
    visibility_range: int = constants.WANDERER_CHASE_BFS_STEPS

    def _step(self, maze: Maze, players: dict[int, Player], turn: int,
              rng: random.Random) -> None:
        """Гонится за ближайшим игроком, иначе делает случайный шаг.

        Случайный шаг не ведёт назад, если только бродяга не в тупике.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел для выбора направления.

        Raises:
            LevelError: Если позиция бродяги или игрока некорректна,
                или игрок недостижим (из ``get_shortest_path``).
        """
        target = self._get_nearest_player(maze, players)
        path = target[1] if target is not None else None

        if path is not None and len(path) <= self.visibility_range:
            next_cell = path[0] if path else self.position
        else:
            neighbors = get_neighbors(maze, self.position)
            forward = [cell for cell in neighbors if cell != self.previous]
            next_cell = rng.choice(forward or neighbors)

        self.previous = self.position
        self.position = next_cell

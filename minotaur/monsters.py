"""Монстры лабиринта: охотник, бродяга и Минотавр."""

import random
from dataclasses import dataclass, field
from typing import ClassVar
from enum import Enum, auto

from minotaur import constants
from minotaur import custom_types
from minotaur.exceptions import LevelError
from minotaur.pathfinding import (
    get_bfs_distances, get_neighbors, get_shortest_path,
)


class Mode(Enum):
    """Режимы поведения бродяги.

    Attributes:
        CHASE: Погоня за игроком в зоне видимости.
        SEARCH: Поиск игрока в клетке, где его видели последний раз.
        WANDER: Случайное блуждание.
    """

    CHASE = auto()
    SEARCH = auto()
    WANDER = auto()


class Phase(Enum):
    """Фазы Минотавра.

    Attributes:
        AIM: Метка поставлена, Минотавр готовится к прыжку.
        REST: Минотавр отдыхает после прыжка.
    """

    AIM = auto()
    REST = auto()


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
    position: custom_types.Cell
    step_rate: ClassVar[int]
    turns_until_move: int = 0

    def tick(
        self,
        maze: custom_types.Maze,
        players: dict[str, custom_types.Player],
        turn: int,
        rng: random.Random,
        is_freeze_active: bool = False,
        key: custom_types.Cell | None = None,
    ) -> None:
        """Делает один ход монстра, меняя ``position``.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел.
            is_freeze_active: Активен ли бонус (заморозка).
            key: Позиция ключа (``Level.key``), ``None``, если ключ
                уже поднят кем-то из игроков.
        """
        if is_freeze_active:
            return

        if self.turns_until_move > 1:
            self.turns_until_move -= 1
        else:
            self.turns_until_move = self.step_rate
            self._step(maze, players, turn, rng, key)

    def _get_nearest_player(
        self,
        maze: custom_types.Maze,
        players: dict[str, custom_types.Player]
    ) -> tuple[custom_types.Player, list[custom_types.Cell] | None] | None:
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

    def _step(
        self,
        maze: custom_types.Maze,
        players: dict[str, custom_types.Player],
        turn: int,
        rng: random.Random,
        key: custom_types.Cell | None = None,
    ) -> None:
        """Делает один ход монстра, меняя ``position``.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел.
            key: Позиция ключа или ``None``, если ключ поднят.

        Raises:
            NotImplementedError: Всегда, метод переопределяется
                в наследниках.
        """
        raise NotImplementedError


@dataclass
class Hunter(Monster):
    """Монстр, который перехватывает или преследует ближайшего игрока.

    Attributes:
        symbol: Символ охотника на карте, ``HUNTER``.
        step_rate: Охотник ходит раз в ``HUNTER_STEP_RATE`` ходов.
        turns_until_move: Количество ходов, оставшихся до хода охотника.
    """

    symbol: ClassVar[str] = constants.HUNTER
    step_rate: ClassVar[int] = constants.HUNTER_STEP_RATE
    turns_until_move: int = 0

    def _step(
        self,
        maze: custom_types.Maze,
        players: dict[str, custom_types.Player],
        turn: int,
        rng: random.Random,
        key: custom_types.Cell | None = None,
    ) -> None:
        """Делает шаг раз в ``HUNTER_STEP_RATE`` ходов.

        Пока ключ не поднят, охотник пытается перехватить ближайшего
        игрока на его пути к ключу. Если ни в одну клетку этого пути
        охотник не успевает раньше игрока или ключ уже поднят, он
        идёт к игроку по кратчайшему пути. Если охотник уже стоит
        на клетке игрока или в точке перехвата, он остаётся на месте.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел, охотником не используется.
            key: Позиция ключа или ``None``, если ключ поднят.

        Raises:
            LevelError: Если позиция охотника некорректна
                (из ``get_shortest_path``).
        """
        target = self._get_nearest_player(maze, players)

        if target is None:
            return

        player, path = target
        is_key_taken = key is None

        if not is_key_taken:
            intercept = self._get_intercept_cell(maze, player.pos, key)
            if intercept is not None:
                path = get_shortest_path(maze, self.position, intercept)

        if path:
            self.position = path[0]

    def _get_intercept_cell(
        self,
        maze: custom_types.Maze,
        player_pos: custom_types.Cell,
        key: custom_types.Cell,
    ) -> custom_types.Cell | None:
        """Находит ближайшую к игроку клетку его пути к ключу,
        в которую охотник успевает не позже игрока.

        Args:
            maze: Карта лабиринта.
            player_pos: Позиция игрока.
            key: Позиция ключа.

        Returns:
            Клетка перехвата или ``None``, если охотник никуда
            не успевает раньше игрока или ключ недостижим.
        """
        try:
            player_path = get_shortest_path(maze, player_pos, key)
        except LevelError:
            return None

        hunter_distances = get_bfs_distances(maze, self.position)
        for player_steps, cell in enumerate(player_path, start=1):
            hunter_steps = hunter_distances.get(cell)
            if (hunter_steps is not None
                    and hunter_steps * self.step_rate <= player_steps):
                return cell
        return None


@dataclass
class Wanderer(Monster):
    """Монстр, который бродит и преследует ближайшего игрока.

    Attributes:
        symbol: Символ бродяги на карте, ``WANDERER``.
        step_rate: Бродяга ходит раз в ``WANDERER_STEP_RATE`` ходов.
        turns_until_move: Количество ходов, оставшихся до хода бродяги.
        last_seen: Клетка, где бродяга последний раз видел игрока,
            или ``None``, если он никого не ищет.
        previous: Клетка, с которой бродяга пришёл, или ``None``.
        visibility_range: Расстояние до игрока в шагах, в пределах
            которого бродяга начинает погоню.
    """

    symbol: ClassVar[str] = constants.WANDERER
    step_rate: ClassVar[int] = constants.WANDERER_STEP_RATE
    turns_until_move: int = 0
    last_seen: custom_types.Cell | None = None
    previous: custom_types.Cell | None = None
    visibility_range: int = constants.WANDERER_CHASE_BFS_STEPS

    def _get_mode(self, path: list[custom_types.Cell] | None) -> Mode:
        """Определяет режим монстра.

        Args:
            path: BFS путь до ближайшего игрока.

        Returns:
            Mode.CHASE, если путь есть и игрок в зоне видимости.
            Mode.SEARCH, если потерял игрока из виду, но видел ранее.
            Mode.WANDER в иных ситуациях.
        """
        if path is not None and len(path) <= self.visibility_range:
            return Mode.CHASE
        if self.last_seen is not None and self.last_seen != self.position:
            return Mode.SEARCH
        return Mode.WANDER

    def _step(
        self,
        maze: custom_types.Maze,
        players: dict[str, custom_types.Player],
        turn: int,
        rng: random.Random,
        key: custom_types.Cell | None = None,
    ) -> None:
        """Гонится за игроком, ищет его или делает случайный шаг.

        Режим выбирает ``_get_mode``. В погоне бродяга запоминает
        клетку игрока и, потеряв его из виду, идёт к ней. Случайный
        шаг не ведёт назад, если только бродяга не в тупике.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел для выбора направления.
            key: Позиция ключа, бродягой не используется.

        Raises:
            LevelError: Если позиция бродяги или игрока некорректна,
                или игрок недостижим (из ``get_shortest_path``).
        """
        target = self._get_nearest_player(maze, players)
        path = target[1] if target is not None else None
        next_cell = self.position

        match self._get_mode(path):
            case Mode.CHASE:
                next_cell = path[0] if path else self.position
                self.last_seen = path[-1] if path else None
            case Mode.SEARCH:
                assert self.last_seen is not None
                next_cell = get_shortest_path(
                    maze, self.position, self.last_seen, 1)[0]
            case _:
                if self.last_seen == self.position:
                    self.last_seen = None
                neighbors = get_neighbors(maze, self.position)
                forward = [cell for cell in neighbors if cell != self.previous]
                next_cell = rng.choice(forward or neighbors)

        self.previous = self.position
        self.position = next_cell


@dataclass
class Minotaur(Monster):
    """Босс 7-го уровня: метит область у игрока и прыгает в неё.

    Минотавр не ходит по коридорам, а повторяет три фазы. Прицел:
    выбирает ближайшего живого игрока и отмечает область 3 × 3 вокруг
    клетки, куда приземлится. Через ``MINOTAUR_AIM_TURNS`` ходов он
    прыгает туда через стены, но не дальше ``MINOTAUR_JUMP_RANGE``
    клеток. Затем ``MINOTAUR_REST_TURNS`` ходов стоит на месте.
    Заморозка останавливает все фазы и тем самым продлевает отдых.

    Расстояния считаются по прямой, без учёта стен: сумма разностей
    строк и столбцов.

    Attributes:
        symbol: Символ Минотавра на карте, ``MINOTAUR``.
        step_rate: Минотавр действует каждый ход.
        turns_until_move: Количество ходов, оставшихся до действия.
        phase: Текущая фаза, ``None``, пока цель не выбрана.
        turns_left: Сколько ходов осталось до конца текущей фазы.
        landing: Клетка, куда Минотавр прыгнет, или ``None``.
        mark: Клетки метки прыжка; пусто, если метки нет.
        jump_area: Клетки, накрытые прыжком на этом ходу. Игроки
            в них пойманы. Пусто во все остальные ходы.
    """

    symbol: ClassVar[str] = constants.MINOTAUR
    step_rate: ClassVar[int] = 1
    turns_until_move: int = 0
    phase: Phase | None = None
    turns_left: int = 0
    landing: custom_types.Cell | None = None
    mark: set[custom_types.Cell] = field(default_factory=set)
    jump_area: set[custom_types.Cell] = field(default_factory=set)

    def tick(
        self,
        maze: custom_types.Maze,
        players: dict[str, custom_types.Player],
        turn: int,
        rng: random.Random,
        is_freeze_active: bool = False,
        key: custom_types.Cell | None = None,
    ) -> None:
        """Делает одно действие Минотавра, если нет заморозки.

        Перед действием очищает ``jump_area``: область прыжка опасна
        только в тот ход, когда Минотавр приземлился.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел для выбора клетки прыжка.
            is_freeze_active: Активна ли заморозка.
            key: Позиция ключа, Минотавром не используется.
        """
        self.jump_area = set()
        super().tick(maze, players, turn, rng, is_freeze_active, key)

    def _step(
        self,
        maze: custom_types.Maze,
        players: dict[str, custom_types.Player],
        turn: int,
        rng: random.Random,
        key: custom_types.Cell | None = None,
    ) -> None:
        """Переводит Минотавра по фазам: прицел, прыжок, отдых.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            turn: Номер текущего хода.
            rng: Генератор случайных чисел для выбора клетки прыжка.
            key: Позиция ключа, Минотавром не используется.
        """
        if self.phase is Phase.REST:
            self.turns_left -= 1
            if self.turns_left <= 0:
                self.phase = None
            return

        if self.phase is Phase.AIM:
            self.turns_left -= 1
            if self.turns_left <= 0:
                self._jump()
            return

        self._aim(maze, players, rng)

    def _aim(
        self,
        maze: custom_types.Maze,
        players: dict[str, custom_types.Player],
        rng: random.Random,
    ) -> None:
        """Выбирает клетку прыжка и ставит метку вокруг неё.

        Если живых игроков нет, Минотавр остаётся без цели.

        Args:
            maze: Карта лабиринта.
            players: Игроки, находящиеся в лабиринте.
            rng: Генератор случайных чисел для выбора клетки прыжка.
        """
        alive = [player.pos for player in players.values()
                 if player.is_alive]
        if not alive:
            return

        target = min(alive, key=lambda cell: _distance(self.position, cell))
        self.landing = self._get_landing(maze, target, rng)
        self.mark = _get_area(maze, self.landing)
        self.phase = Phase.AIM
        self.turns_left = constants.MINOTAUR_AIM_TURNS

    def _get_landing(
        self,
        maze: custom_types.Maze,
        target: custom_types.Cell,
        rng: random.Random,
    ) -> custom_types.Cell:
        """Находит проход в пределах прыжка, ближайший к цели.landing

        Args:
            maze: Карта лабиринта.
            target: Клетка, в которую Минотавр целится.
            rng: Генератор случайных чисел для выбора среди равных.

        Returns:
            Сама цель, если она в пределах прыжка, иначе ближайший
            к ней проход, до которого Минотавр допрыгнет.
        """
        reachable = [
            custom_types.Cell(row, col)
            for row in range(len(maze))
            for col in range(len(maze[row]))
            if maze[row][col] == constants.FILE_AIR
            and _distance(self.position, custom_types.Cell(row, col))
            <= constants.MINOTAUR_JUMP_RANGE
        ]
        best = min(_distance(cell, target) for cell in reachable)
        return rng.choice([cell for cell in reachable
                           if _distance(cell, target) == best])

    def _jump(self) -> None:
        """Прыгает на ``landing``, накрывает метку и уходит на отдых."""
        self.position = self.landing
        self.jump_area = self.mark
        self.landing = None
        self.mark = set()
        self.phase = Phase.REST
        self.turns_left = constants.MINOTAUR_REST_TURNS


def _distance(first: custom_types.Cell, second: custom_types.Cell) -> int:
    """Считает расстояние между клетками без учёта стен.

    Args:
        first: Первая клетка.
        second: Вторая клетка.

    Returns:
        Сумма разностей строк и столбцов.
    """
    return abs(first.row - second.row) + abs(first.col - second.col)


def _get_area(
    maze: custom_types.Maze,
    center: custom_types.Cell,
) -> set[custom_types.Cell]:
    """Возвращает проходы в квадрате 3 × 3 вокруг клетки.

    Args:
        maze: Карта лабиринта.
        center: Центр квадрата.

    Returns:
        Клетки квадрата, которые лежат на карте и не являются стенами.
    """
    return {
        custom_types.Cell(center.row + d_row, center.col + d_col)
        for d_row in (-1, 0, 1)
        for d_col in (-1, 0, 1)
        if 0 <= center.row + d_row < len(maze)
        and 0 <= center.col + d_col < len(maze[0])
        and maze[center.row + d_row][center.col + d_col]
        == constants.FILE_AIR
    }

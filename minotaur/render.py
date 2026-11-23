"""Отрисовка игрового кадра: карта с туманом войны и HUD.

Все функции чистые: возвращают строку, не пишут в stdout.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from colorama import Fore, Style

from minotaur.constants import (
    COMPASS,
    EXIT,
    FILE_WALL,
    FREEZE,
    HUNTER,
    KEY,
    MAX_LEVEL,
    PLAYER,
    TORCH,
    WALL_CORNER,
    WALL_HORIZONTAL,
    WALL_VERTICAL,
)
from minotaur.custom_types import Cell

if TYPE_CHECKING:  # pragma: no cover
    from minotaur.custom_types import Maze
    from minotaur.game import GameState


# Палитра цветов. Значение — пара (цвет, стиль).
COLORS: dict[str, tuple[str, str]] = {
    "player": (Fore.GREEN, Style.BRIGHT),
    "key": (Fore.YELLOW, Style.BRIGHT),
    "exit": (Fore.CYAN, Style.BRIGHT),
    "hunter": (Fore.RED, Style.BRIGHT),
    "wanderer": (Fore.MAGENTA, Style.BRIGHT),
    "freeze": (Fore.LIGHTCYAN_EX, Style.BRIGHT),
    "torch": (Fore.LIGHTYELLOW_EX, Style.BRIGHT),
    "compass": (Fore.LIGHTBLUE_EX, Style.BRIGHT),
    "wall": (Fore.LIGHTBLACK_EX, Style.NORMAL),
    "memory": (Fore.LIGHTBLACK_EX, Style.DIM),
    "compass_hint": (Fore.LIGHTBLUE_EX, Style.DIM),
    "hud": (Fore.WHITE, Style.NORMAL),
    "hud_accent": (Fore.LIGHTWHITE_EX, Style.BRIGHT),
}


def _paint(symbol: str, color_key: str, color: bool) -> str:
    """Красит один символ.

    Args:
        symbol: Символ для вывода.
        color_key: Ключ из COLORS.
        color: Включён ли цвет.

    Returns:
        Строка с ANSI-кодами или без них.
    """
    if not color:
        return symbol
    fg, st = COLORS[color_key]
    return f"{st}{fg}{symbol}{Style.RESET_ALL}"


def _is_wall(maze: Maze, row: int, col: int) -> bool:
    """Проверяет, что клетка в границах и это стена.

    Args:
        maze: Лабиринт.
        row: Строка.
        col: Столбец.

    Returns:
        True, если клетка — стена.
    """
    if row < 0 or col < 0:
        return False
    if row >= len(maze):
        return False
    if col >= len(maze[row]):
        return False
    return maze[row][col] == FILE_WALL


def _wall_symbol(maze: Maze, row: int, col: int) -> str:
    """Подбирает символ стены по соседям.

    Логика:
    - есть стена слева или справа => горизонтальная '-'
    - есть стена сверху или снизу => вертикальная '|'
    - иначе угол/перекрёсток '+'

    Args:
        maze: Лабиринт.
        row: Строка.
        col: Столбец.

    Returns:
        Один из WALL_HORIZONTAL / WALL_VERTICAL / WALL_CORNER.
    """
    left = _is_wall(maze, row, col - 1)
    right = _is_wall(maze, row, col + 1)
    up = _is_wall(maze, row - 1, col)
    down = _is_wall(maze, row + 1, col)

    horizontal = left or right
    vertical = up or down

    if horizontal and vertical:
        return WALL_CORNER
    if horizontal:
        return WALL_HORIZONTAL
    if vertical:
        return WALL_VERTICAL
    return WALL_CORNER


def _symbol_at(
    state: GameState,
    row: int,
    col: int,
    visible: set,
    memory: bool,
) -> tuple[str, str]:
    """Определяет символ и цвет клетки с учётом приоритетов.

    Приоритет: игрок > монстр > ключ > бонус > выход > пол.
    В памяти (memory=True) монстры не рисуются.

    Args:
        state: Состояние игры.
        row: Строка.
        col: Столбец.
        visible: Множество видимых сейчас клеток.
        memory: Режим «запомненной» клетки.

    Returns:
        Пара (символ, ключ цвета).
    """
    cell = Cell(row, col)

    if cell == state.level.player:
        return PLAYER, "player"

    if not memory:
        for sym, pos in state.level.monsters:
            if pos == cell:
                return sym, "hunter" if sym == HUNTER else "wanderer"

    if state.level.key is not None and cell == state.level.key:
        return KEY, "key"

    bonus = state.level.bonuses.get(cell)
    if bonus is not None:
        if bonus == FREEZE:
            return FREEZE, "freeze"
        if bonus == TORCH:
            return TORCH, "torch"
        if bonus == COMPASS:
            return COMPASS, "compass"
        return bonus, "torch"

    if cell == state.level.exit:
        return EXIT, "exit"

    if cell in getattr(state, "compass_path", []):
        return "·", "compass_hint"

    return " ", "wall"


def _render_cell(
    state: GameState,
    row: int,
    col: int,
    visible: set,
    explored: set,
    color: bool,
) -> str:
    """Рисует одну клетку карты.

    Args:
        state: Состояние игры.
        row: Строка.
        col: Столбец.
        visible: Видимые клетки.
        explored: Запомненные клетки.
        color: Включён ли цвет.

    Returns:
        Строка — один символ с цветом.
    """
    cell = Cell(row, col)
    maze = state.level.maze

    if maze[row][col] == FILE_WALL:
        return _paint(_wall_symbol(maze, row, col), "wall", color)

    if cell not in visible and cell not in explored:
        return " "

    if cell not in visible and cell in explored:
        sym, _ = _symbol_at(state, row, col, visible, memory=True)
        if sym == " ":
            return " "
        return _paint(sym, "memory", color)

    sym, color_key = _symbol_at(state, row, col, visible, memory=False)
    return _paint(sym, color_key, color)


def _render_hud(state: GameState) -> str:
    """Собирает строки HUD.

    Args:
        state: Состояние игры.

    Returns:
        Многострочный текст HUD.
    """
    level_num = state.level_num + 1
    key_state = "взят" if state.level.key is None else "нет"
    freeze = (
        f"да ({state.level.freeze_turns})"
        if state.level.freeze_turns > 0
        else "нет"
    )
    torch = "да" if state.level.torch_active else "нет"
    compass = "активна" if state.compass_path else "нет"

    lines = [
        f"Уровень {level_num}/{MAX_LEVEL} | Счёт: {state.score} | "
        f"Ходы: {state.turn}",
        f"Ключ: {key_state} | Заморозка: {freeze} | "
        f"Факел: {torch} | Компас: {compass}",
    ]
    return "\n".join(lines)


def render(state: GameState, color: bool = True) -> str:
    """Собирает готовый кадр (карта + HUD) в строку.

    Args:
        state: Состояние игры.
        color: Включать ли ANSI-цвета.

    Returns:
        Готовый кадр одной строкой (со строками через \\n).
    """
    visible = set(getattr(state, "visible_cells", set()) or set())
    if not visible:
        # Резервный путь: если игровая логика не дала visible_cells,
        # считаем видимыми хотя бы клетки explored и клетку игрока.
        visible = set(getattr(state, "explored", set()))
        visible.add(state.level.player)

    explored = set(getattr(state, "explored", set()))
    maze = state.level.maze

    rows: list[str] = []
    for r in range(len(maze)):
        line_chars: list[str] = []
        for c in range(len(maze[r])):
            line_chars.append(
                _render_cell(state, r, c, visible, explored, color)
            )
        rows.append("".join(line_chars))

    hud = _render_hud(state)
    if color:
        hud = (
            f"{COLORS['hud_accent'][1]}{COLORS['hud_accent'][0]}{hud}"
            f"{Style.RESET_ALL}"
        )

    hint = (
        "w/a/s/d — движение, пробел — ждать, "
        "h — помощь, p — пауза"
    )
    if color:
        hint = _paint(hint, "hud", color)

    return "\n".join([*rows, "", hud, "", hint])


def draw(state: GameState, color: bool = True) -> None:
    """Очищает экран и печатает кадр одним write.

    Args:
        state: Состояние игры.
        color: Включать ли цвет.
    """
    frame = render(state, color=color)
    sys.stdout.write("\033[H\033[J" + frame + "\n")
    sys.stdout.flush()

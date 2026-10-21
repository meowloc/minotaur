"""Создание заготовки лабиринта и первого пути обходом в глубину."""

import random

from minotaur import constants
from minotaur.custom_types import Cell
from minotaur.exceptions import GenerationError


def init_map_gen(level_num):
    """Создать независимые строки карты, полностью заполненные стенами.

    Args:
        level_num: Индекс уровня, начиная с 0.

    Returns:
        Матрица размера LEVEL_SIZES, включая внешние стены.

    Raises:
        GenerationError: Номер уровня или размеры карты недопустимы.
    """
    if (type(level_num) is not int
            or not 0 <= level_num < constants.MAX_LEVEL):
        raise GenerationError("Недопустимый номер уровня.")
    height, width = constants.LEVEL_SIZES[level_num]
    if (type(height) is not int or type(width) is not int
            or height < 5 or width < 5):
        raise GenerationError("Размеры карты - целые числа не меньше 5.")
    return [[constants.FILE_WALL for _ in range(width)]
            for _ in range(height)]


def making_labyrinth(map_matrix, rng=None):
    """Проложить первый путь от игрока до выхода с помощью DFS.
    Если кратко: находим игрока, находим выход.
    Рандомно выбираем путь от игрока до выхода, и по этому пути
    убираем стены и ставим '.'.

    Args:
        map_matrix: Карта после init_map_gen и place_exit_and_player.
            Матрица изменяется на месте.
        rng: Генератор random.Random для воспроизводимости.

    Returns:
        Та же матрица с проходами и сохранёнными игроком и выходом.
        Ветки, исследованные до достижения выхода, тоже остаются проходами.

    Raises:
        GenerationError: Нет игрока, выхода или пути между ними.
    """
    if rng is None:
        rng = random.Random()

    start = None
    exit_pos = None
    height = len(map_matrix)
    for row in range(height):
        for col in range(len(map_matrix[row])):
            if map_matrix[row][col] == constants.PLAYER:
                start = Cell(row, col)
            elif map_matrix[row][col] == constants.EXIT:
                exit_pos = Cell(row, col)

    if start is None or exit_pos is None:
        raise GenerationError("На карте должны быть игрок и выход.")

    width = len(map_matrix[0])
    stack = [start]
    visited = [start]
    directions = [(dr * 2, dc * 2)
                  for dr, dc in constants.DIRECTIONS.values()]

    while len(stack) > 0:
        if stack[-1] == exit_pos:
            return map_matrix

        row, col = stack[-1]
        candidates = []
        for dr, dc in directions:
            next_row = row + dr
            next_col = col + dc
            if next_row <= 0 or next_row >= height - 1:
                continue
            if next_col <= 0 or next_col >= width - 1:
                continue
            next_cell = Cell(next_row, next_col)
            if next_cell in visited:
                continue
            candidates.append(next_cell)

        if len(candidates) == 0:
            stack.pop()
            continue

        next_cell = rng.choice(candidates)
        next_row, next_col = next_cell

        # Убираем стену посередине между двумя клетками.
        wall_row = (row + next_row) // 2
        wall_col = (col + next_col) // 2
        map_matrix[wall_row][wall_col] = constants.FILE_AIR
        if next_cell != exit_pos:
            map_matrix[next_row][next_col] = constants.FILE_AIR

        visited.append(next_cell)
        stack.append(next_cell)

    raise GenerationError("Не удалось проложить путь до выхода.")

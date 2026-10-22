"""Создание заготовки лабиринта и первого пути обходом в глубину."""

import random

from minotaur import constants
from minotaur.custom_types import Cell
from minotaur.exceptions import GenerationError, LevelError


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


def add_loops(map_matrix, count, rng=None):
    """Открыть ровно count перегородок между существующими коридорами.

    Args:
        map_matrix: Связная карта после making_labyrinth.
            Изменяется на месте; новые коридоры не достраиваются.
        count: Сколько перегородок открыть между коридорами.
        rng: Генератор random.Random для воспроизводимости.

    Returns:
        Та же карта с дополнительными путями. Старые проходы, игрок,
        выход и внешние стены сохраняются. При count=0 карта не меняется.

    Raises:
        LevelError: Неверное число проходов, карта меньше 5x5,
            строки разной длины или недостаточно подходящих стен.
            При ошибке карта не изменяется.
    """
    if type(count) is not int or count < 0:
        raise LevelError("Число дополнительных проходов недопустимо.")

    height = len(map_matrix)
    if height < 5 or len(map_matrix[0]) < 5:
        raise LevelError("Размеры карты должны быть не меньше 5.")
    width = len(map_matrix[0])
    for row in map_matrix:
        if len(row) != width:
            raise LevelError("Строки карты должны быть одной длины.")

    if count == 0:
        return map_matrix
    if rng is None:
        rng = random.Random()

    # У перегородки одна координата чётная, другая нечётная.
    walls = []
    for row in range(1, height - 1):
        for col in range(1, width - 1):
            if map_matrix[row][col] != constants.FILE_WALL:
                continue
            if row % 2 == 0 and col % 2 == 1:
                first = map_matrix[row - 1][col]
                second = map_matrix[row + 1][col]
            elif row % 2 == 1 and col % 2 == 0:
                first = map_matrix[row][col - 1]
                second = map_matrix[row][col + 1]
            else:
                continue
            if (first != constants.FILE_WALL
                    and second != constants.FILE_WALL):
                walls.append(Cell(row, col))

    if count > len(walls):
        raise LevelError("Недостаточно стен для дополнительных проходов.")

    for _ in range(count):
        wall = rng.choice(walls)
        map_matrix[wall.row][wall.col] = constants.FILE_AIR
        walls.remove(wall)

    return map_matrix

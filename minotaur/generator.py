"""Создание полного лабиринта обходом в глубину и добавление обходных путей."""

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


def making_labyrinth(map_matrix, player, exit_pos, rng=None):
    """Построить полный лабиринт с помощью DFS со стеком и возвратом.
    Координаты игрока и выхода передаются отдельно от карты.
    Обходим все комнаты с нечётными координатами, открывая проходы
    между ними. Достижение выхода не останавливает обход.

    Args:
        map_matrix: Карта из стен после init_map_gen. Изменяется на месте.
        player: Координата игрока Cell из place_exit_and_player.
        exit_pos: Координата выхода Cell из place_exit_and_player.
        rng: Генератор random.Random для воспроизводимости.

    Returns:
        Та же матрица только из стен и проходов, без символов объектов.
        Все комнаты соединены, между ними ровно один путь.
        Дополнительные пути затем создаёт add_loops.

    Raises:
        GenerationError: Неверные размеры карты или координаты объектов.
    """
    if rng is None:
        rng = random.Random()

    height = len(map_matrix)
    if height < 5 or len(map_matrix[0]) < 5:
        raise GenerationError("Размеры карты должны быть не меньше 5.")
    width = len(map_matrix[0])
    for cell in (player, exit_pos):
        if type(cell) is not Cell:
            raise GenerationError("Нужны координаты игрока и выхода Cell.")
        if type(cell.row) is not int or type(cell.col) is not int:
            raise GenerationError("Координаты должны быть целыми числами.")
        if (not 0 < cell.row < height - 1 or not 0 < cell.col < width - 1
                or cell.row % 2 == 0 or cell.col % 2 == 0):
            raise GenerationError("Координаты должны быть внутри и нечётными.")

    map_matrix[player.row][player.col] = constants.FILE_AIR
    stack = [player]
    visited = [player]
    directions = [(dr * 2, dc * 2)
                  for dr, dc in constants.DIRECTIONS.values()]

    while len(stack) > 0:
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
        map_matrix[next_row][next_col] = constants.FILE_AIR

        visited.append(next_cell)
        stack.append(next_cell)

    return map_matrix


def add_loops(map_matrix, count, rng=None):
    """Открыть ровно count перегородок между существующими коридорами.

    Args:
        map_matrix: Связная карта после making_labyrinth.
            Изменяется на месте; новые коридоры не достраиваются.
        count: Сколько перегородок открыть между коридорами.
        rng: Генератор random.Random для воспроизводимости.

    Returns:
        Та же карта с дополнительными путями. Старые проходы
        и внешние стены сохраняются. При count=0 карта не меняется.

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
            if (first == constants.FILE_AIR
                    and second == constants.FILE_AIR):
                walls.append(Cell(row, col))

    if count > len(walls):
        raise LevelError("Недостаточно стен для дополнительных проходов.")

    for _ in range(count):
        wall = rng.choice(walls)
        map_matrix[wall.row][wall.col] = constants.FILE_AIR
        walls.remove(wall)

    return map_matrix

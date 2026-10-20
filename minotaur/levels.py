"""Размещение выхода и игрока."""

import random

from minotaur import constants
from minotaur.exceptions import PlaceError


def place_exit_and_player(map_matrix, rng=None):
    """Разместить выход и наиболее удалённого игрока вдоль внешних стен.

    Args:
        map_matrix: Карта из стен после init_map_gen, изменяемая на месте.
        rng: Генератор random.Random для воспроизводимости.

    Returns:
        Пара координат (игрок, выход). До прокладки коридоров используется
        манхэттенское расстояние между потенциальными клетками прохода.
        Оба объекта стоят на нечётных координатах в клетке от внешней стены.
        При одинаковом расстоянии клетка выбирается случайно.

    Raises:
        PlaceError: Карта недопустима или содержит что-либо кроме стен.
    """
    if rng is None:
        rng = random.Random()

    height = len(map_matrix)
    if height < 5:
        raise PlaceError("Высота карты должна быть не меньше 5.")
    width = len(map_matrix[0])
    if width < 5:
        raise PlaceError("Ширина карты должна быть не меньше 5.")

    for row in map_matrix:
        if len(row) != width:
            raise PlaceError("Строки карты должны быть одной длины.")
        for cell in row:
            if cell != constants.FILE_WALL:
                raise PlaceError(
                    "Для расстановки нужна карта только из стен."
                )

    cells = []
    for row in range(1, height - 1, 2):
        for col in range(1, width - 1, 2):
            if (row == 1 or row == height - 2
                    or col == 1 or col == width - 2):
                cells.append((row, col))

    exit_pos = rng.choice(cells)
    exit_row, exit_col = exit_pos

    max_distance = -1
    farthest_cells = []
    for row, col in cells:
        distance = abs(row - exit_row) + abs(col - exit_col)
        if distance > max_distance:
            max_distance = distance
            farthest_cells = [(row, col)]
        elif distance == max_distance:
            farthest_cells.append((row, col))

    player = rng.choice(farthest_cells)
    player_row, player_col = player
    map_matrix[exit_row][exit_col] = constants.EXIT
    map_matrix[player_row][player_col] = constants.PLAYER
    return player, exit_pos

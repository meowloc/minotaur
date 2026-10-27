"""Размещение объектов, сохранение и загрузка уровня."""

import json
import random

from minotaur import constants
from minotaur.custom_types import Cell, Level
from minotaur.exceptions import LevelError, PlaceError
from minotaur.pathfinding import get_bfs_distances


def place_exit_and_player(map_matrix, rng=None):
    """Разместить выход и наиболее удалённого игрока вдоль внешних стен.

    Args:
        map_matrix: Карта из стен после init_map_gen. Не изменяется.
        rng: Генератор random.Random для воспроизводимости.

    Returns:
        Пара Cell (игрок, выход). До прокладки коридоров используется
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
                cells.append(Cell(row, col))

    exit_pos = rng.choice(cells)
    exit_row, exit_col = exit_pos

    max_distance = -1
    farthest_cells = []
    for cell in cells:
        distance = abs(cell.row - exit_row) + abs(cell.col - exit_col)
        if distance > max_distance:
            max_distance = distance
            farthest_cells = [cell]
        elif distance == max_distance:
            farthest_cells.append(cell)

    player = rng.choice(farthest_cells)
    return player, exit_pos


def validate_level(source):
    """Проверить Level после генерации или JSON-файл перед загрузкой.

    Args:
        source: Объект Level или путь к JSON-файлу UTF-8.

    Returns:
        Проверенный словарь данных, чтобы не читать файл повторно.
        Исходный Level не изменяется.

    Raises:
        LevelError: Файл недоступен, содержит неверный JSON или не UTF-8;
            отсутствуют обязательные поля или неверна структура данных;
            карта меньше 5x5, строки разной длины, есть посторонние символы
            или проходы на внешней границе; координаты не являются парой
            целых чисел, лежат в стене или вне внутренней части карты;
            неизвестен тип монстра или бонуса; игрок, монстры или бонусы
            занимают одну клетку; объект недостижим для игрока;
            остаток заморозки не является целым неотрицательным числом
            или состояние факела не является булевым значением.
    """
    try:
        if type(source) is Level:
            data = {
                'maze': source.maze,
                'player': source.player,
                'exit': source.exit,
                'key': source.key,
                'monsters': source.monsters,
                'bonuses': list(source.bonuses.items()),
                'freeze_turns': source.freeze_turns,
                'torch_active': source.torch_active,
            }
        else:
            with open(source, encoding='utf-8') as file:
                data = json.load(file)

        maze = data['maze']
        if type(maze) is not list or len(maze) < 5:
            raise LevelError('Карта должна содержать не меньше пяти строк.')
        for row in maze:
            if type(row) is not list or len(row) < 5:
                raise LevelError('В строке карты нужен список из 5+ клеток.')
            if len(row) != len(maze[0]):
                raise LevelError('Строки карты должны быть одной длины.')
            for symbol in row:
                if symbol not in (constants.FILE_WALL, constants.FILE_AIR):
                    raise LevelError('На карте допустимы только # и .')
        for row in range(len(maze)):
            for col in range(len(maze[0])):
                if row in (0, len(maze) - 1) or col in (0, len(maze[0]) - 1):
                    if maze[row][col] != constants.FILE_WALL:
                        raise LevelError('Граница карты должна быть стеной.')

        positions = [data['player'], data['exit']]
        if data['key'] is not None:
            positions.append(data['key'])
        if (type(data['monsters']) is not list
                or type(data['bonuses']) is not list):
            raise LevelError('Монстры и бонусы должны быть списками.')
        for symbol, position in data['monsters']:
            if symbol not in (constants.HUNTER, constants.WANDERER):
                raise LevelError('Неизвестный тип монстра.')
            positions.append(position)
        bonus_cells = set()
        for position, symbol in data['bonuses']:
            if symbol not in (constants.FREEZE, constants.TORCH,
                              constants.COMPASS):
                raise LevelError('Неизвестный тип бонуса.')
            cell = Cell(*position)
            if cell in bonus_cells:
                raise LevelError('В одной клетке несколько бонусов.')
            bonus_cells.add(cell)
            positions.append(position)
        for position in positions:
            if type(position) not in (list, tuple, Cell) or len(position) != 2:
                raise LevelError('Нужна пара координат.')
            row, col = position
            if type(row) is not int or type(col) is not int:
                raise LevelError('Координаты должны быть целыми числами.')
            if not (0 < row < len(maze) - 1 and 0 < col < len(maze[0]) - 1):
                raise LevelError('Объект за пределами внутренней части карты.')
            if maze[row][col] != constants.FILE_AIR:
                raise LevelError('Объект находится в стене.')
        occupied_cells = {Cell(*data['player'])}
        for symbol, position in data['monsters']:
            cell = Cell(*position)
            if cell in occupied_cells:
                raise LevelError(
                    'Координаты монстра совпадают с игроком или монстром.'
                )
            occupied_cells.add(cell)
        for cell in bonus_cells:
            if cell in occupied_cells:
                raise LevelError(
                    'Координаты бонуса совпадают с игроком или монстром.'
                )
        distances = get_bfs_distances(maze, Cell(*data['player']))
        for position in positions:
            if Cell(*position) not in distances:
                raise LevelError('Объект недостижим для игрока.')
        freeze_turns = data.get('freeze_turns', 0)
        if type(freeze_turns) is not int or freeze_turns < 0:
            raise LevelError('Остаток заморозки должен быть целым и >= 0.')
        if type(data.get('torch_active', False)) is not bool:
            raise LevelError('Состояние факела должно быть true или false.')
        return data
    except LevelError:
        raise
    except (OSError, KeyError, TypeError, ValueError, AttributeError) as error:
        raise LevelError(f'Не удалось проверить уровень: {error}')


def save_level(level, path):
    """Записать готовый уровень в JSON-файл UTF-8.

    Args:
        level: Корректный объект Level.
        path: Путь к файлу в существующей папке. Старый файл заменяется.

    Raises:
        LevelError: Ошибка преобразования или записи.
    """
    try:
        data = {
            'maze': level.maze,
            'player': level.player,
            'exit': level.exit,
            'key': level.key,
            'monsters': level.monsters,
            'bonuses': list(level.bonuses.items()),
            'freeze_turns': level.freeze_turns,
            'torch_active': level.torch_active,
        }
        text = json.dumps(data, ensure_ascii=False, indent=2)
        with open(path, 'w', encoding='utf-8') as file:
            file.write(text + '\n')
    except (OSError, TypeError, ValueError, AttributeError) as error:
        raise LevelError(f'Не удалось сохранить уровень: {error}')


def load_level(path):
    """Проверить JSON-файл UTF-8 и создать Level.

    Args:
        path: Путь к файлу. Карта — список списков символов # и .,
            координаты — [row, col].
            Монстры — пары [символ, координата], бонусы — наоборот.
            key равен null после подбора. Без полей эффектов они выключены.

    Returns:
        Уровень с координатами Cell и сохранёнными эффектами.

    Raises:
        LevelError: Некорректный уровень, ошибка чтения или преобразования.
    """
    try:
        data = validate_level(path)
        maze = data['maze']
        player = Cell(*data['player'])
        exit_pos = Cell(*data['exit'])
        key = None
        if data['key'] is not None:
            key = Cell(*data['key'])
        monsters = []
        for symbol, position in data['monsters']:
            monsters.append((symbol, Cell(*position)))
        bonuses = {}
        for position, symbol in data['bonuses']:
            bonuses[Cell(*position)] = symbol
        freeze_turns = data.get('freeze_turns', 0)
        torch_active = data.get('torch_active', False)
        return Level(maze, player, exit_pos, key, monsters, bonuses,
                     freeze_turns, torch_active)
    except LevelError:
        raise
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise LevelError(f'Не удалось загрузить уровень: {error}')

"""Размещение объектов, сохранение и загрузка уровня."""

import json
import random

from minotaur import constants
from minotaur.custom_types import Cell, Level, Player
from minotaur.exceptions import LevelError, PlaceError
from minotaur.generator import add_loops, init_map_gen, making_labyrinth
from minotaur.pathfinding import get_bfs_distances, get_shortest_path


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


def place_objects(level: Level, level_num, rng=None):
    """Расставить монстров, ключ и бонусы на готовой карте.

    Args:
        level: Уровень с готовой картой, игроком и выходом, без ключа,
            монстров и бонусов. Объекты добавляются в него на месте;
            карта и позиции игрока и выхода не меняются.
        level_num: Индекс уровня с нуля для выбора LEVEL_CONTENTS.
        rng: Генератор random.Random для воспроизводимости.

    Returns:
        Тот же Level с расставленными объектами после проверки.
        Монстры стоят не ближе MONSTER_MIN_SPAWN_DISTANCE шагов от
        игрока и вне одного кратчайшего пути от игрока к выходу.
        Ключ и бонусы доступны по проходам. Выход и монстры
        при поиске пути не считаются препятствиями.
        Все объекты занимают разные клетки.

    Raises:
        PlaceError: Неверный индекс уровня,
            уровень уже содержит объекты или не хватает клеток.
        LevelError: Передан не Level, карта или координаты неверны.
    """
    if (type(level_num) is not int
            or not 0 <= level_num < constants.MAX_LEVEL):
        raise PlaceError("Недопустимый номер уровня.")
    if type(level) is not Level:
        raise LevelError("Для расстановки нужен объект Level.")
    validate_level(level)
    if level.key is not None or level.monsters or level.bonuses:
        raise PlaceError("Уровень уже содержит ключ, монстров или бонусы.")
    if rng is None:
        rng = random.Random()

    hunters, wanderers, bonus_count, _ = constants.LEVEL_CONTENTS[level_num]
    if not level.players:
        raise PlaceError("На уровне нет игроков.")
    player_positions = {player.pos for player in level.players.values()}
    player = next(iter(level.players.values())).pos
    distances = get_bfs_distances(level.maze, player)
    exit_path = get_shortest_path(level.maze, player, level.exit)

    key_cells = []
    monster_cells = []
    free_cells = []
    for cell in distances:
        if cell in player_positions or cell == level.exit:
            continue
        free_cells.append(cell)
        key_cells.append(cell)
        if (distances[cell] >= constants.MONSTER_MIN_SPAWN_DISTANCE
                and cell not in exit_path):
            monster_cells.append(cell)

    monster_count = hunters + wanderers
    if len(monster_cells) < monster_count:
        raise PlaceError("Недостаточно клеток для монстров.")
    if len(free_cells) < monster_count + bonus_count + 1:
        raise PlaceError("Недостаточно клеток для всех объектов.")

    # Ключ не должен занять последнее нужное место для монстра.
    if len(monster_cells) == monster_count:
        key_cells = [cell for cell in key_cells if cell not in monster_cells]
    if not key_cells:
        raise PlaceError("Нет доступной клетки для ключа.")
    level.key = rng.choice(key_cells)
    free_cells.remove(level.key)
    if level.key in monster_cells:
        monster_cells.remove(level.key)

    symbols = [constants.HUNTER] * hunters + [constants.WANDERER] * wanderers
    for symbol in symbols:
        cell = rng.choice(monster_cells)
        level.monsters.append((symbol, cell))
        monster_cells.remove(cell)
        free_cells.remove(cell)

    bonus_symbols = [constants.FREEZE, constants.TORCH, constants.COMPASS]
    for _ in range(bonus_count):
        cell = rng.choice(free_cells)
        level.bonuses[cell] = rng.choice(bonus_symbols)
        free_cells.remove(cell)

    validate_level(level)
    return level


def generate_level(level_num, rng=None):
    """Создать карту и расставить все объекты уровня.

    Args:
        level_num: Индекс уровня, начиная с нуля.
        rng: Общий генератор random.Random для всех этапов.

    Returns:
        Проверенный Level с ключом, монстрами и бонусами.

    Raises:
        GenerationError: Неверный номер уровня или размер карты.
        PlaceError: На полученной карте не хватает мест для объектов.
        LevelError: Невозможно добавить проходы или уровень некорректен.
    """
    if rng is None:
        rng = random.Random()
    maze = init_map_gen(level_num)
    player, exit_pos = place_exit_and_player(maze, rng)
    making_labyrinth(maze, player, exit_pos, rng)
    add_loops(maze, constants.LEVEL_CONTENTS[level_num][3], rng)
    level = Level(maze=maze, exit=exit_pos, key=None,
                  players={1: Player(id=1, nick=None, pos=player,
                                     last_played_round=None)})
    return place_objects(level, level_num, rng)


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
            неизвестен тип монстра или бонуса; любые два объекта
            занимают одну клетку; объект недостижим для игрока;
            остаток заморозки не является целым неотрицательным числом
            или состояние факела не является булевым значением.
    """
    try:
        # ДАННЫЕ: получаем поля уровня из объекта Level или JSON-файла.
        if type(source) is Level:
            data = {
                'maze': source.maze,
                'players': {str(player_id): {
                    'id': player.id, 'nick': player.nick,
                    'pos': player.pos, 'is_connected': player.is_connected,
                    'is_alive': player.is_alive, 'is_ready': player.is_ready,
                    'last_played_round': player.last_played_round,
                    'torch_active': player.torch_active,
                    'steps': player.steps, 'score': player.score,
                } for player_id, player in source.players.items()},
                'exit': source.exit,
                'key': source.key,
                'monsters': source.monsters,
                'bonuses': list(source.bonuses.items()),
                'freeze_turns': source.freeze_turns,
            }
        else:
            with open(source, encoding='utf-8') as file:
                data = json.load(file)

        # КАРТА: проверяем размеры, символы.
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
        # ГРАНИЦЫ: вся внешняя рамка карты должна состоять из стен.
        for row in range(len(maze)):
            for col in range(len(maze[0])):
                if row in (0, len(maze) - 1) or col in (0, len(maze[0]) - 1):
                    if maze[row][col] != constants.FILE_WALL:
                        raise LevelError('Граница карты должна быть стеной.')

        # ОБЪЕКТЫ: собираем названия и позиции в общий список.
        # Проверяем списки монстров и бонусов и допустимость их символов.
        if type(data['players']) is not dict:
            raise LevelError('Игроки должны быть словарём.')
        player_positions = []
        for player_id, player in data['players'].items():
            if type(player) is not dict:
                raise LevelError('Некорректные данные игрока.')
            if type(player.get('id')) is not int\
                    or str(player['id']) != str(player_id):
                raise LevelError('Некорректный идентификатор игрока.')
            if player.get('nick') is not None\
                    and type(player['nick']) is not str:
                raise LevelError('Некорректный никнейм игрока.')
            for field in ('is_connected', 'is_alive',
                          'is_ready', 'torch_active'):
                if type(player.get(field, False)) is not bool:
                    raise LevelError('Некорректное состояние игрока.')
            if (player.get('last_played_round') is not None
                    and type(player['last_played_round']) is not int):
                raise LevelError('Некорректные данные игрока.')
            for field in ('steps', 'score'):
                if type(player.get(field, 0)) is not int:
                    raise LevelError('Некорректные данные игрока.')
            player_positions.append(player['pos'])
        objects = [('игрока', position) for position in player_positions]
        objects.append(('выхода', data['exit']))
        if data['key'] is not None:
            objects.append(('ключа', data['key']))
        if (type(data['monsters']) is not list
                or type(data['bonuses']) is not list):
            raise LevelError('Монстры и бонусы должны быть списками.')
        for symbol, position in data['monsters']:
            if symbol not in (constants.HUNTER, constants.WANDERER):
                raise LevelError('Неизвестный тип монстра.')
            objects.append(('монстра', position))
        for position, symbol in data['bonuses']:
            if symbol not in (constants.FREEZE, constants.TORCH,
                              constants.COMPASS):
                raise LevelError('Неизвестный тип бонуса.')
            objects.append(('бонуса', position))
        # КООРДИНАТЫ: два целых числа, клетка внутри карты и не в стене.
        # Занятые клетки храним вместе с названиями объектов для ошибок.
        occupied_cells = {}
        for name, position in objects:
            if type(position) not in (list, tuple, Cell) or len(position) != 2:
                raise LevelError('Нужна пара координат.')
            row, col = position
            if type(row) is not int or type(col) is not int:
                raise LevelError('Координаты должны быть целыми числами.')
            if not (0 < row < len(maze) - 1 and 0 < col < len(maze[0]) - 1):
                raise LevelError('Объект за пределами внутренней части карты.')
            if maze[row][col] != constants.FILE_AIR:
                raise LevelError('Объект находится в стене.')
            # СОВПАДЕНИЯ: никакие два объекта не могут занимать одну клетку.
            cell = Cell(*position)
            if cell in occupied_cells:
                raise LevelError(
                    f'Координаты {name} и {occupied_cells[cell]} совпадают.'
                )
            occupied_cells[cell] = name
        # ДОСТИЖИМОСТЬ: до каждого объекта должен быть путь от игрока.
        if player_positions:
            distances = get_bfs_distances(maze, Cell(*player_positions[0]))
            for cell in occupied_cells:
                if cell not in distances:
                    raise LevelError('Объект недостижим для игрока.')
        # ЭФФЕКТЫ: заморозка — целое число >= 0, факел — True или False.
        freeze_turns = data.get('freeze_turns', 0)
        if type(freeze_turns) is not int or freeze_turns < 0:
            raise LevelError('Остаток заморозки должен быть целым и >= 0.')
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
            'players': {str(player_id): {
                'id': player.id, 'nick': player.nick,
                'pos': player.pos, 'is_connected': player.is_connected,
                'is_alive': player.is_alive, 'is_ready': player.is_ready,
                'last_played_round': player.last_played_round,
                'torch_active': player.torch_active,
                'steps': player.steps, 'score': player.score,
            } for player_id, player in level.players.items()},
            'exit': level.exit,
            'key': level.key,
            'monsters': level.monsters,
            'bonuses': list(level.bonuses.items()),
            'freeze_turns': level.freeze_turns,
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
        players = {}
        for player_id, player in data['players'].items():
            players[int(player_id)] = Player(
                id=player['id'], nick=player.get('nick'),
                pos=Cell(*player['pos']),
                is_connected=player.get('is_connected', False),
                is_alive=player.get('is_alive', True),
                is_ready=player.get('is_ready', False),
                last_played_round=player.get('last_played_round'),
                torch_active=player.get('torch_active', False),
                steps=player.get('steps', 0), score=player.get('score', 0),
            )
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
        return Level(maze=maze, exit=exit_pos, key=key, players=players,
                     monsters=monsters, bonuses=bonuses,
                     freeze_turns=freeze_turns)
    except LevelError:
        raise
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise LevelError(f'Не удалось загрузить уровень: {error}')

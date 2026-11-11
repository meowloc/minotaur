"""Константы игры: размеры уровней, символы, настройки монстров и бонусов.

Attributes:
    LEVEL_SIZES: Размеры карт уровней в виде пар (высота, ширина).
    LEVEL_CONTENTS: Наполнение уровней в виде кортежей (охотники,
        бродяги, бонусы, дополнительно сломанные стены).
    MAX_LEVEL: Количество уровней; номера уровней от 0 до MAX_LEVEL - 1.
    FILE_AIR: Символ прохода в файле уровня.
    FILE_WALL: Символ стены в файле уровня.
    PLAYER: Символ игрока на экране.
    ALLY: Символ второго игрока на экране (в онлайн-игре).
    KEY: Символ ключа.
    EXIT: Символ выхода.
    HUNTER: Символ охотника.
    WANDERER: Символ бродяги.
    FREEZE: Символ бонуса заморозки.
    TORCH: Символ бонуса факела.
    COMPASS: Символ бонуса компаса.
    WALL_VERTICAL: Символ вертикальной стены на экране.
    WALL_HORIZONTAL: Символ горизонтальной стены на экране.
    WALL_CORNER: Символ угла стены на экране.
    DIRECTIONS: Направления движения и смещения (строка, столбец).
    PLAYER_ID_LENGTH: Длина идентификатора игрока: строка ровно из стольких
        символов из 0–9 и a–f, например ``"e482ab"``.
    MONSTER_MIN_SPAWN_DISTANCE: Минимальное расстояние в шагах
        от игрока до монстра при расстановке.
    HUNTER_STEP_RATE: Охотник ходит раз в столько ходов.
    WANDERER_STEP_RATE: Бродяга ходит раз в столько ходов.
    WANDERER_CHASE_BFS_STEPS: Расстояние в шагах, с которого бродяга
        замечает игрока и начинает погоню.
    BONUS_FREEZE_STEPS: Сколько ходов монстры стоят после заморозки.
    BONUS_COMPASS_RANGE: Сколько клеток пути показывает компас.
    BONUS_TORCH_RADIUS: На сколько клеток факел увеличивает обзор.
    VIEW_RADIUS: Радиус обзора игрока в тумане войны.
    SCORE_PER_LEVEL: Очки за прохождение уровня.
    SCORE_SPEED_BASE: Базовое число очков за скорость прохождения.
    SCORE_PER_BONUS: Очки за подобранный бонус.
    KEY_BINDINGS: Клавиши управления и соответствующие действия.
    PALETTE: Палитра цветом, используемая для отображения контента на экране.
    LEGEND: Легенда для экрана помощи: символ, название и описание.
"""

LEVEL_SIZES = [(7, 9), (9, 11), (11, 13), (13, 15),
               (15, 17), (19, 21), (21, 23)]

LEVEL_CONTENTS = [(0, 1, 1, 2), (1, 0, 1, 3), (1, 1, 2, 4), (1, 2, 2, 6),
                  (2, 1, 3, 8), (2, 2, 3, 10), (3, 2, 4, 12)]

MAX_LEVEL = len(LEVEL_SIZES)

FILE_AIR = "."
FILE_WALL = "#"

PLAYER = "P"
ALLY = "P"
KEY = "K"
EXIT = "E"
HUNTER = "H"
WANDERER = "W"
FREEZE = "*"
TORCH = "^"
COMPASS = "?"

WALL_VERTICAL = "|"
WALL_HORIZONTAL = "-"
WALL_CORNER = "+"

DIRECTIONS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}

PLAYER_ID_LENGTH = 6

MONSTER_MIN_SPAWN_DISTANCE = 7

HUNTER_STEP_RATE = 1
WANDERER_STEP_RATE = 1
WANDERER_CHASE_BFS_STEPS = 5

BONUS_FREEZE_STEPS = 3
BONUS_COMPASS_RANGE = 8
BONUS_TORCH_RADIUS = 2

VIEW_RADIUS = 5

SCORE_PER_LEVEL = 100
SCORE_SPEED_BASE = 300
SCORE_PER_BONUS = 20

KEY_BINDINGS = {
    "w": "up",
    "a": "left",
    "s": "down",
    "d": "right",
    " ": "wait",
    "h": "help",
    "p": "pause",
}

PALETTE = {
    "wall": "#5b6478",
    "floor": "#3d4558",
    "seen": "#2c3242",
    "player": "#4d8dff",
    "ally": "#a3e635",
    "key": "#ffd23f",
    "exit": "#3ccf7a",
    "exit_locked": "#6b7a72",
    "hunter": "#ff5a5a",
    "wanderer": "#ff9f43",
    "minotaur": "#b56bff",
    "jump": "#ff4fa0",
    "freeze": "#6fd3ff",
    "torch": "#fff3c4",
    "compass": "#5eead4",
    "text": "#c9d1e0",
    "muted": "#7b8496",
}


def _plural(n: int, word: str) -> str:
    """Возвращает число с английским существительным в правильной форме.

    Args:
        n: Количество предметов.
        word: Существительное в единственном числе.

    Returns:
        "1 turn", если n равно 1, иначе форму множественного числа,
        например "3 turns".
    """
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _every(n: int, word: str = "turn") -> str:
    """Возвращает обозначение периода для фразы, начинающейся с "every".

    Args:
        n: Сколько единиц длится период.
        word: Единица измерения в единственном числе.

    Returns:
        "turn", если n равно 1 (как в "every turn"), иначе "2 turns".
    """
    return word if n == 1 else f"{n} {word}s"


LEGEND = [
    (FILE_AIR, "Air", "Free passage"),
    (WALL_CORNER + WALL_HORIZONTAL + WALL_VERTICAL, "Wall", "Impassable"),
    (PLAYER, "Player", "Moves one cell per turn"),
    (KEY, "Key", "Required to open the exit"),
    (EXIT, "Exit", "Opens only if the key has been picked up"),
    (HUNTER, "Hunter",
     "Cuts you off on the way to the key, then follows you "
     f"by the shortest path, one step every {_every(HUNTER_STEP_RATE)}"),
    (WANDERER, "Wanderer",
     f"Moves every {_every(WANDERER_STEP_RATE)}, wanders randomly, "
     f"chases you within {_plural(WANDERER_CHASE_BFS_STEPS, 'step')} "
     "and checks where it saw you last"),
    (FREEZE, "Freeze",
     f"Monsters stand still for {_plural(BONUS_FREEZE_STEPS, 'turn')}"),
    (TORCH, "Torch",
     f"View radius +{BONUS_TORCH_RADIUS} until the end of the level"),
    (COMPASS, "Compass",
     f"Shows the next {_plural(BONUS_COMPASS_RANGE, 'cell')} "
     "of the path to the key or the exit"),
]

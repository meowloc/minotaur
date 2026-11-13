"""Константы игры: размеры уровней, символы, настройки монстров и бонусов.

Attributes:
    LEVEL_SIZES: Размеры карт уровней в виде пар (высота, ширина).
    LEVEL_CONTENTS: Наполнение уровней в виде кортежей (минотавры, охотники,
        бродяги, бонусы, дополнительно сломанные стены).
    MAX_LEVEL: Количество уровней; номера уровней от 0 до MAX_LEVEL - 1.
    FILE_AIR: Символ прохода в файле уровня.
    FILE_WALL: Символ стены в файле уровня.
    PLAYER: Символ игрока на экране.
    ALLY: Символ второго игрока на экране (в онлайн-игре).
    KEY: Символ ключа.
    EXIT: Символ выхода.
    MINOTAUR: Символ минотавра.
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
        цифр 0–9, например ``"000001"``.
    MONSTER_MIN_SPAWN_DISTANCE: Минимальное расстояние в шагах
        от игрока до монстра при расстановке.
    MINOTAUR_JUMP_RANGE: Дальность прыжка Минотавра в клетках; стены
        прыжку не мешают.
    MINOTAUR_AIM_TURNS: Сколько ходов требуется Минотавру на совершение прыжка.
    MINOTAUR_REST_TURNS: Сколько ходов Минотавр отдыхает после прыжка.
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

LEVEL_CONTENTS = [
    (0, 0, 1, 1, 2),
    (0, 1, 0, 1, 3),
    (0, 1, 1, 2, 4),
    (0, 1, 2, 2, 6),
    (0, 2, 1, 3, 8),
    (0, 2, 2, 3, 10),
    (1, 2, 2, 4, 12)
]

MAX_LEVEL = len(LEVEL_SIZES)

FILE_AIR = "."
FILE_WALL = "#"

PLAYER = "P"
ALLY = "P"
KEY = "K"
EXIT = "E"
MINOTAUR_MARK = "!"
MINOTAUR = "M"
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

MINOTAUR_JUMP_RANGE = 6
MINOTAUR_AIM_TURNS = 2
MINOTAUR_REST_TURNS = 3

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


def _plural(n: int, forms: tuple[str, str, str]) -> str:
    """Возвращает число с существительным в нужной форме.

    Args:
        n: Количество предметов.
        forms: Формы слова для 1, 2 и 5 предметов,
            например ``("ход", "хода", "ходов")``.

    Returns:
        Строка вида "1 ход", "3 хода" или "11 ходов".
    """
    if n % 10 == 1 and n % 100 != 11:
        form = forms[0]
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        form = forms[1]
    else:
        form = forms[2]
    return f"{n} {form}"


def _every(n: int) -> str:
    """Возвращает, как часто монстр ходит.

    Args:
        n: Раз в сколько ходов монстр делает шаг.

    Returns:
        "каждый ход", если n равно 1, иначе, например, "раз в 2 хода".
    """
    if n == 1:
        return "каждый ход"
    return f"раз в {_plural(n, TURN_FORMS)}"


TURN_FORMS = ("ход", "хода", "ходов")

LEGEND = [
    (FILE_AIR, "Проход", "Свободная клетка"),
    (WALL_CORNER + WALL_HORIZONTAL + WALL_VERTICAL, "Стена", "Не пройти"),
    (PLAYER, "Игрок", "Ходит на одну клетку за ход"),
    (KEY, "Ключ", "Нужен, чтобы открыть выход"),
    (EXIT, "Выход", "Открывается, только если ключ подобран"),
    (MINOTAUR_MARK, "Метка прыжка",
     "Сюда Минотавр приземлится на следующем ходу. Видна даже в тени: "
     "уйдите из области, иначе вас поймают"),
    (MINOTAUR, "Минотавр",
     "Финальный босс 7-го уровня. Отмечает область 3 × 3 вокруг "
     "ближайшего игрока, на следующем ходу прыгает туда через стены "
     "не дальше "
     f"{_plural(MINOTAUR_JUMP_RANGE, ('клетки', 'клеток', 'клеток'))} "
     f"и отдыхает {_plural(MINOTAUR_REST_TURNS, TURN_FORMS)}"),
    (HUNTER, "Охотник",
     "Перехватывает вас по дороге к ключу, а потом идёт за вами "
     f"кратчайшим путём, шаг {_every(HUNTER_STEP_RATE)}"),
    (WANDERER, "Бродяга",
     f"Ходит {_every(WANDERER_STEP_RATE)}, бродит наугад, гонится "
     "за вами в пределах "
     f"{_plural(WANDERER_CHASE_BFS_STEPS, ('шага', 'шагов', 'шагов'))} "
     "и проверяет место, где видел вас в последний раз"),
    (FREEZE, "Заморозка",
     f"Монстры стоят на месте {_plural(BONUS_FREEZE_STEPS, TURN_FORMS)}"),
    (TORCH, "Факел",
     f"Радиус обзора +{BONUS_TORCH_RADIUS} до конца уровня"),
    (COMPASS, "Компас",
     "Показывает "
     f"{_plural(BONUS_COMPASS_RANGE, ('клетку', 'клетки', 'клеток'))} "
     "пути к ключу или выходу"),
]

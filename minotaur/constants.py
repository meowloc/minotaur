# level sizes
LEVEL_SIZES = [(7, 9), (9, 11), (11, 13), (13, 15),
               (15, 17), (19, 21), (21, 23)]

# hunters, wanderers, bonuses, extra broken walls
LEVEL_CONTENTS = [(0, 1, 1, 2), (1, 0, 1, 3), (1, 1, 2, 4), (1, 2, 2, 6),
                  (2, 1, 3, 8), (2, 2, 3, 10), (3, 2, 4, 12)]

MAX_LEVEL = len(LEVEL_SIZES)

# level files
FILE_AIR = "."
FILE_WALL = "#"

# objects
PLAYER = "P"
KEY = "K"
EXIT = "E"
HUNTER = "H"
WANDERER = "W"
FREEZE = "*"
TORCH = "^"
COMPASS = "?"

# wall types
WALL_VERTICAL = "|"
WALL_HORIZONTAL = "-"
WALL_CORNER = "+"

DIRECTIONS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}

# generation
MONSTER_MIN_SPAWN_DISTANCE = 7

# monsters
HUNTER_STEP_RATE = 2
WANDERER_STEP_RATE = 1
WANDERER_CHASE_BFS_STEPS = 5

# bonuses
BONUS_FREEZE_STEPS = 3
BONUS_COMPASS_RANGE = 8
BONUS_TORCH_RADIUS = 2

# fog of war
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


def _plural(n: int, word: str) -> str:
    """Возвращает число с английским существительным в правильной форме.

    Args:
        n: Количество предметов.
        word: Существительное в единственном числе.

    Returns:
        "1 turn", если n равно 1, иначе форму множественного числа, например "3 turns".
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
     "Follows you by the shortest path, one step every "
     f"{_every(HUNTER_STEP_RATE)}"),
    (WANDERER, "Wanderer",
     f"Moves every {_every(WANDERER_STEP_RATE)}, wanders randomly, "
     f"chases you within {_plural(WANDERER_CHASE_BFS_STEPS, 'step')}"),
    (FREEZE, "Freeze",
     f"Monsters stand still for {_plural(BONUS_FREEZE_STEPS, 'turn')}"),
    (TORCH, "Torch",
     f"View radius +{BONUS_TORCH_RADIUS} until the end of the level"),
    (COMPASS, "Compass",
     f"Shows the next {_plural(BONUS_COMPASS_RANGE, 'cell')} "
     "of the path to the key or the exit"),
]

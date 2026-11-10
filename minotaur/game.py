from minotaur import constants
from minotaur.custom_types import Player, Level, Cell
from minotaur.exceptions import MovementError, MinotaurError


def player_move(direction: tuple, player: Player,
                level: Level, other_player: Player):
    """Перемещает игрока на одну клетку лабиринта.

    Проверяет стены, монстров и других игроков.
    При успешном ходе обновляет позицию и число шагов.

    Args:
        direction: Смещение по строке и столбцу.
        player: Игрок, выполняющий перемещение.
        level: Уровень с лабиринтом и монстрами.
        other_player: Напарник, занимающий другую клетку.

    Raises:
        MovementError: Если клетка занята стеной
            или другим игроком."""
    new_pos = direction[0] + player.pos.row, direction[1] + player.pos.col
    if level.maze[new_pos[0]][new_pos[1]] == constants.FILE_WALL:
        raise MovementError(
               "Ход в этом направление невозможен там стена"
        )
    elif any(monster_pos == Cell(*new_pos)
             for _, monster_pos in level.monsters):
        player.is_alive = False
    elif (other_player.pos.row, other_player.pos.col) == new_pos:
        raise MovementError(
            "Ход в этом направление невозможен там ваш союзник"
        )
    else:
        player.pos = Cell(*new_pos)
        player.steps += 1


def check_bonuses(bonus: str, player: Player, level: Level):
    """Применяет эффект бонуса к игроку.

    Заморозка останавливает монстров на заданное
    количество ходов. Факел активирует освещение,
    а компас включает отображение маршрута.

    Args:
        bonus: Тип бонуса, который получает игрок.
        player: Игрок, которому применяется бонус.
        level: Уровень, состояние которого изменяется.

    Raises:
        MinotaurError: Если передан неизвестный бонус."""
    if bonus == constants.FREEZE:
        level.is_freeze_active = True
        level.freeze_turns = constants.BONUS_FREEZE_STEPS
    elif bonus == constants.TORCH:
        player.torch_active = True
    elif bonus == constants.COMPASS:
        player.compass_active = True
    else:
        raise MinotaurError(f"Бонус {bonus} не находится в константах")

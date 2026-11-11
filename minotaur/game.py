from minotaur import constants
from minotaur.custom_types import Level, Cell
from minotaur.exceptions import MovementError, LevelError


def move_player(direction: tuple, player_id: str, level: Level):
    """Перемещает игрока на одну клетку лабиринта.

    Проверяет стены, монстров и других игроков.
    При успешном ходе обновляет позицию и число шагов.

    Args:
        direction: Смещение по строке и столбцу.
        player_id: id игрока, который совершил передвижение.
        level: Уровень с лабиринтом и монстрами.

    Raises:
        MovementError: Если клетка занята стеной
            или другим игроком.
    """
    curr_player = level.players[player_id]
    new_pos = Cell(direction[0] + curr_player.pos.row,
                   direction[1] + curr_player.pos.col)
    other_players = {
        key: value
        for key, value in level.players.items()
        if key != player_id
    }
    if level.maze[new_pos.row][new_pos.col] == constants.FILE_WALL:
        raise MovementError(
               "Ход невозможен: на пути стена!"
        )
    elif any(new_pos == other_player.pos
             for other_player in other_players.values()):
        raise MovementError(
            "Ход невозможен: на пути напарник!"
        )
    elif any(monster_pos == new_pos
             for _, monster_pos in level.monsters):
        curr_player.is_alive = False
    curr_player.pos = new_pos
    curr_player.steps += 1


def apply_bonus(bonus: str, player_id: str, level: Level):
    """Применяет эффект бонуса к игроку.

    Заморозка останавливает монстров на заданное
    количество ходов. Факел активирует освещение,
    а компас включает отображение маршрута до ключа или выхода.

    Args:
        bonus: Тип бонуса, который получает игрок.
        player_id: id игрока, к которому применяется бонус.
        level: Уровень, состояние которого изменяется.

    Raises:
        LevelError: Если передан неизвестный бонус.
    """
    curr_player = level.players[player_id]
    if bonus == constants.FREEZE:
        level.freeze_turns = constants.BONUS_FREEZE_STEPS
    elif bonus == constants.TORCH:
        curr_player.torch_active = True
    elif bonus == constants.COMPASS:
        curr_player.compass_active = True
    else:
        raise LevelError(f"Бонус {bonus} не находится в константах!")

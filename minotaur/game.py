from minotaur import constants
from minotaur.custom_types import Player, Level, Cell
from minotaur.exceptions import  MovementError, MinotaurError
from minotaur.pathfinding import get_bfs_distances


def player_move(direction:tuple, player: Player, level : Level, other_player: Player):
    """Перемещает игрока на одну клетку в заданном направлении.

       Проверяет наличие стены, монстра или другого игрока
       в целевой клетке. При успешном перемещении обновляет
       позицию игрока и увеличивает счётчик шагов.

       Args:
           direction: Смещение по строке и столбцу лабиринта.
           player: Игрок, для которого выполняется перемещение.
           level: Текущий уровень с лабиринтом, игроками и монстрами.

       Raises:
           MovementError: Если целевая клетка занята стеной
               или другим игроком."""

    new_pos = direction[0] + player.pos.row,  direction[1] + player.pos.col
    if level.maze[new_pos[0]][new_pos[1]] == constants.FILE_WALL:
        raise  MovementError("Ход в этом направление невозможен там стена")
    elif any((monster_pos.row, monster_pos.col) == new_pos for _, monster_pos in level.monsters):
        player.is_alive = False
    elif (other_player.pos.row, other_player.pos.col) == new_pos:
        raise MovementError("Ход в этом направление невозможен там ваш союзник")
    else:
        player.pos = Cell(new_pos[0], new_pos[1])
        player.steps += 1
def check_bonuses(bonus: str, player: Player, level: Level):
        """Проверяет наличия бонуса в клетке, на которой стоит игрок.

        Заморозка устанавливает количество ходов без движения
        монстров. Факел активирует дополнительное освещение.
        Компас строит маршрут к ключу или выходу из лабиринта.

        Args:
            bonus: Тип бонуса, который подобрал игрок.
            player: Игрок, получающий эффект бонуса.
            level: Текущий уровень, состояние которого может измениться.

        Raises:
            MinotaurError: Если передан неизвестный тип бонуса."""
        if bonus == constants.FREEZE:
            level.is_freeze_active = True
            level.freeze_turns = constants.BONUS_FREEZE_STEPS
        elif bonus == constants.TORCH:
            player.torch_active = True
        elif bonus == constants.COMPASS:
            player.compass_active = True
        else:
            raise MinotaurError(f"Бонус {bonus} не находится в константах")




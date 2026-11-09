import minotaur.constants as constant
from minotaur.custom_types import *
from minotaur.exceptions import  MovementError, MinotaurError
from minotaur.pathfiding import *
def player_move(direction, player: Player, level : Level):
    """Движение игрока
    Args:
    direction - направление (вверх, вниз, право, лево)
    player - сам игрок
    level - уровень на котором совершено двиижение


    Raises:
        Ошибку при движение в стену
        Ошибку при врезание в игрока
    """

    new_pos = direction[0] + player.pos[0],  direction[1] + player.pos[1]
    if level.maze[new_pos[0]][new_pos[1]] == "#":
        raise  MovementError("Вы врезались в стену")
    elif any(monster_pos == new_pos for _, monster_pos in level.monsters):
        player.is_alive = False
    elif any(other_player.pos == new_pos for other_player in level.players.values()):
        raise MovementError("Вы врезались в своего напарника")
    else:
        player.pos = new_pos
        player.steps += 1
def apply_bonusses(bonus: str, player: Player, level: Level,  compass_path):
    """Определяет полученный бонус
    Args:
        bonus - бонус который находился в этой клетке
        level - уровень, на котором был подобран бонус
        player - сам игрок
        compass_path путь проложенный компасом
    Return:
        путь проложенный компасом
    Raises:
        Ошибку при получение неизвестного бонуса
        """
    if bonus == constant.FREEZE:
        level.freeze_turns = 3
    elif bonus == constant.TORCH:
        player.torch_active = True
        constant.VIEW_RADIUS += constant.BONUS_TORCH_RADIUS
    elif bonus == constant.COMPASS:
        player.compass_active = True
        compass_path = get_shortest_path(level.maze,player.pos, level.exit if level.is_key_taken else level.key)[:constant.BONUS_COMPASS_RANGE]
    else:
        raise MinotaurError("Этого бонуса нет в списке")
    return  compass_path


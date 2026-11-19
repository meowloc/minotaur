from dataclasses import dataclass, field
import random

from minotaur import constants
from minotaur.custom_types import Level, Cell
from minotaur.exceptions import MovementError, LevelError
from minotaur.monsters import Hunter, Wanderer
from minotaur.pathfinding import get_shortest_path, get_bfs_distances


@dataclass
class GameState:
    """Хранит текущее состояние игры.

    Attributes:
        level: Текущий уровень с лабиринтом и игроками.
        level_num: Номер текущего уровня.
        state: Состояние игры: Round, Win или Lose.
        explored: Множество исследованных клеток лабиринта.
        compass_path: Маршрут компаса до ключа или выхода.
        turn: Количество выполненных игровых ходов.
        score: Количество набранных очков.
    """

    level: Level
    level_num: int
    state: str = "Round"
    explored: set[Cell] = field(default_factory=set)
    compass_path: list[Cell] = field(default_factory=list)
    turn: int = 0
    score: int = 0


def fog(game: GameState, player_id: str):
    """Обновляет видимые и исследованные клетки лабиринта.

    Определяет расстояния от игрока до доступных клеток.
    Сохраняет клетки в пределах радиуса обзора
    и ранее исследованные клетки.

    Args:
        game: Текущее состояние игры.
        player_id: ID игрока, для которого обновляется видимость.
    """
    distances = get_bfs_distances(game.level.maze,
                                  game.level.players[player_id].pos)
    player = game.level.players[player_id]
    player.cells_status["active"] = [
        cell for cell in distances
        if distances[cell] <= constants.VIEW_RADIUS
    ]
    player.cells_status["explored"] = list(game.explored)


def move_player(direction: tuple, player_id: str, level: Level):
    """Перемещает игрока на одну клетку лабиринта.

    Проверяет стены, монстров и других игроков.
    При успешном ходе обновляет позицию и число шагов.

    Args:
        direction: Смещение по строке и столбцу.
        player_id: ID игрока, который совершил передвижение.
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
             for other_player in other_players.values()) and (
            new_pos != level.exit
    ):
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
        player_id: ID игрока, к которому применяется бонус.
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


def key_actions(key: str, level: Level, player_id: str):
    """Обрабатывает нажатие клавиши игроком.

    Выполняет перемещение, ожидание, паузу или вызов помощи.
    Во время паузы разрешает только помощь и снятие паузы.

    Args:
        key: Нажатая клавиша.
        level: Текущий уровень игры.
        player_id: ID игрока, выполняющего действие.
    """
    curr_action = constants.KEY_BINDINGS[key]
    if not level.is_pause_on:
        if curr_action == "wait":
            pass
        elif curr_action in ["up", "down", "left", "right"]:
            move_player(constants.DIRECTIONS[curr_action], player_id, level)
        elif curr_action == "pause":
            level.is_pause_on = True
        elif curr_action == "help":
            level.players[player_id].help_used = True
    else:
        if curr_action == "pause":
            level.is_pause_on = False
        elif curr_action == "help":
            level.players[player_id].help_used = True


def check_collision(player_old_pos: Cell, monster_old_pos: Cell,
                    player_new_pos: Cell, monster_new_pos: Cell):
    """Проверяет столкновение игрока с монстром.

    Учитывает совпадение конечных позиций и ситуацию,
    когда игрок и монстр поменялись местами за один ход.

    Args:
        player_old_pos: Позиция игрока до хода.
        monster_old_pos: Позиция монстра до хода.
        player_new_pos: Позиция игрока после хода.
        monster_new_pos: Позиция монстра после хода.

    Returns:
        True, если произошло столкновение, иначе False.
    """
    return ((player_new_pos == monster_new_pos) or
            ((player_new_pos == monster_old_pos) and
             (player_old_pos == monster_new_pos)))


def lose(game: GameState):
    """Обрабатывает поражение игроков.

    Обнуляет набранные очки и устанавливает
    состояние игры Lose.

    Args:
        game: Текущее состояние игры.
    """
    game.score = 0
    game.state = "Lose"


def player_score(game: GameState, player_id: str):
    """Начисляет игроку очки за прохождение игры.

    Если игрок жив, добавляет ему очки из общего счёта.
    Если игрок погиб, его счёт остаётся без изменений.

    Args:
        game: Текущее состояние игры.
        player_id: ID игрока, которому начисляются очки.
    """
    if game.level.players[player_id].is_alive:
        game.level.players[player_id].score += game.score


def win(game: GameState):
    """Обрабатывает успешное прохождение уровня.

    Начисляет базовые очки за уровень и бонус за скорость,
    сохраняя ранее набранные очки.
    Устанавливает состояние игры Win.

    Args:
        game: Текущее состояние игры.
    """
    game.score = (game.score
                  + constants.SCORE_PER_LEVEL
                  + max(0, constants.SCORE_SPEED_BASE - game.turn))
    game.state = "Win"


def step(game: GameState, player_id: str, action: str,
         wanderer: Wanderer, hunter: Hunter) -> None:
    """Выполняет один игровой ход.

    Обрабатывает действие игрока, исследованные клетки,
    подбор ключа и бонусов, обновление маршрута компаса,
    движение монстров и столкновения.

    Проверяет условия победы и поражения, обновляет
    счёт и номер текущего хода.

    Args:
        game: Текущее состояние игры.
        player_id: ID игрока, выполняющего ход.
        action: Нажатая клавиша.
        wanderer: Блуждающий монстр.
        hunter: Преследующий монстр.

    Raises:
        MovementError: Если клавиша неизвестна,
            действие запрещено или выход закрыт.
    """
    if game.state != "Round":
        return
    curr_level = game.level
    if not curr_level.players[player_id].is_alive:
        return
    other_players = {
        key: value
        for key, value in curr_level.players.items()
        if key != player_id
    }
    curr_level.players[player_id].help_used = False
    player_old_pos = curr_level.players[player_id].pos
    wanderer_old_pos = wanderer.position
    hunter_old_pos = hunter.position
    if action not in constants.KEY_BINDINGS:
        raise MovementError(f"Клавиша {action} не находится в константах!")
    else:
        key_actions(action, curr_level, player_id)
    if curr_level.is_pause_on:
        return
    else:
        if curr_level.players[player_id].help_used:
            return
        elif constants.KEY_BINDINGS[action] == "pause":
            return
        else:
            if player_old_pos != curr_level.players[player_id].pos:
                game.explored.add(player_old_pos)
                fog(game, player_id)
            if curr_level.key == curr_level.players[player_id].pos:
                curr_level.key = None
            if (curr_level.players[player_id].pos == curr_level.exit
                    and curr_level.is_key_taken):
                if all(
                        player.pos == curr_level.exit or not player.is_alive
                        for player in other_players.values()
                ):
                    win(game)
                    for current_id in curr_level.players:
                        player_score(game, current_id)
                    return
            elif (curr_level.players[player_id].pos == curr_level.exit
                    and not curr_level.is_key_taken):
                raise MovementError("Нельзя открыть выход без ключа!")
            if curr_level.players[player_id].pos in curr_level.bonuses:
                bonus = curr_level.bonuses.pop(
                    curr_level.players[player_id].pos
                )
                apply_bonus(bonus, player_id, curr_level)
                game.score += constants.SCORE_PER_BONUS
            if curr_level.players[player_id].compass_active:
                game.compass_path = get_shortest_path(
                    curr_level.maze,
                    curr_level.players[player_id].pos,
                    curr_level.exit
                    if curr_level.key is None
                    else curr_level.key,
                    constants.BONUS_COMPASS_RANGE
                )
            is_freeze_active = curr_level.freeze_turns > 0
            hunter.tick(curr_level.maze, curr_level.players,
                        game.turn, random.Random(0),
                        is_freeze_active, curr_level.key)
            wanderer.tick(curr_level.maze, curr_level.players,
                          game.turn, random.Random(0),
                          is_freeze_active, curr_level.key)
            curr_level.monsters = [(hunter.symbol, hunter.position),
                                   (wanderer.symbol, wanderer.position)]
            if is_freeze_active:
                curr_level.freeze_turns -= 1
            if ((check_collision(player_old_pos, wanderer_old_pos,
                                 curr_level.players[player_id].pos,
                                 wanderer.position))
                    or (check_collision(player_old_pos, hunter_old_pos,
                                        curr_level.players[player_id].pos,
                                        hunter.position))):
                curr_level.players[player_id].is_alive = False
            for player in other_players.values():
                if (check_collision(player.pos, wanderer_old_pos,
                                    player.pos, wanderer.position)
                        or check_collision(player.pos, hunter_old_pos,
                                           player.pos, hunter.position)):
                    player.is_alive = False
            if all(not player.is_alive
                   for player in curr_level.players.values()):
                lose(game)
                for player in curr_level.players.keys():
                    player_score(game, player)
                return
            game.turn += 1

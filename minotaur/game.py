from dataclasses import dataclass, field
import random

from minotaur import constants
from minotaur.custom_types import Level, Cell
from minotaur.exceptions import MovementError, LevelError
from minotaur.monsters import Monster
from minotaur.pathfinding import get_shortest_path, get_bfs_distances


@dataclass
class GameState:
    """Хранит текущее состояние игры.

    Attributes:
        level: Текущий уровень с лабиринтом и игроками.
        level_num: Номер текущего уровня.
        state: Состояние игры: Round/Win/Lose.
        explored: Множество исследованных клеток лабиринта.
        players_old_pos: Исходные позиции игроков текущего раунда.
        turn: Количество выполненных игровых ходов.
        score: Количество набранных очков.
        message: Сообщение о результате последнего действия.
        rng: Генератор случайных чисел для поведения монстров.
    """

    level: Level
    level_num: int
    state: str = "Round"
    explored: set[Cell] = field(default_factory=set)
    players_old_pos: dict[str, Cell] = field(default_factory=dict)
    turn: int = 0
    score: int = 0
    message: str = ""
    rng: random.Random = field(
        default_factory=random.Random
    )


def fog(game: GameState, player_id: str):
    """Обновляет освещённые клетки и полутень.

    Вычисляет расстояния от игрока до доступных клеток.
    Факел увеличивает радиус света только для владельца.
    В освещённой области видны карта и монстры.
    В кольце полутени видна карта, но не монстры.
    Открытые клетки сохраняются в истории исследования.

    Args:
        game: Текущее состояние игры.
        player_id: ID игрока, для которого обновляется видимость.
    """
    player = game.level.players[player_id]
    distances = get_bfs_distances(game.level.maze, player.pos)

    light_radius = constants.VIEW_RADIUS
    if player.torch_active:
        light_radius += constants.BONUS_TORCH_RADIUS

    shadow_radius = light_radius + constants.VIEW_RADIUS

    visible = {
        cell for cell, distance in distances.items()
        if distance <= light_radius
    }

    shadow = {
        cell for cell, distance in distances.items()
        if light_radius < distance <= shadow_radius
    }

    game.explored.update(visible | shadow)

    player.cells_status["active"] = list(visible)
    player.cells_status["discovered"] = list(shadow)


def move_player(direction: tuple, player_id: str, level: Level) -> None:
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


def apply_bonus(bonus: str, player_id: str, level: Level) -> None:
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


def key_actions(key: str, level: Level, player_id: str) -> None:
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
                    player_new_pos: Cell, monster_new_pos: Cell) -> bool:
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


def lose(game: GameState) -> None:
    """Обрабатывает поражение игроков.

    Устанавливает состояние поражения, когда все игроки погибли.

    Args:
        game: Текущее состояние игры.
    """
    game.state = "Lose"
    player_score(game)


def player_score(game: GameState) -> None:
    """Начисляет игроку очки за прохождение игры.

    Добавляет каждому игроку очки из общего счёта.

    Args:
        game: Текущее состояние игры.
    """
    if game.state == "Win":
        game.score = (game.score
                      + constants.SCORE_PER_LEVEL
                      + max(0, constants.SCORE_SPEED_BASE - game.turn))
    for player in game.level.players.values():
        player.score += game.score
    game.score = 0


def win(game: GameState) -> None:
    """Обрабатывает успешное прохождение уровня.

    Начисляет базовые очки за уровень и бонус за скорость,
    сохраняя ранее набранные очки.
    Устанавливает состояние игры Win.

    Args:
        game: Текущее состояние игры.
    """
    game.state = "Win"
    player_score(game)


def step(game: GameState, player_id: str, action: str,
         monsters_in_level: list[Monster]) -> None:
    """Выполняет действие игрока и обновляет состояние раунда.

    Обрабатывает движение, ожидание, паузу и вызов помощи.
    Сохраняет исходную позицию игрока для проверки столкновений.
    Обновляет туман войны, подбирает ключ и применяет бонусы.
    Пересчитывает маршрут компаса при его наличии.

    После действий всех живых игроков перемещает монстров.
    Проверяет столкновения, включая обмен позициями.
    Учитывает заморозку монстров и уменьшает её длительность.
    Проверяет условия победы и поражения.
    При завершении раунда увеличивает счётчик ходов.

    Args:
        game: Текущее состояние игры.
        player_id: ID игрока, выполняющего действие.
        action: Нажатая клавиша.
        monsters_in_level: Монстры текущего уровня.

    Raises:
        MovementError: Если клавиша неизвестна или ход невозможен.
    """

    if game.turn == 0:
        fog(game, player_id)

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
    if action not in constants.KEY_BINDINGS:
        raise MovementError(f"Клавиша {action} не находится в константах!")
    else:
        if (player_id in game.players_old_pos
                and constants.KEY_BINDINGS[action] not in ("pause", "help")):
            raise MovementError("Ваша очередь еще не настала")
        key_actions(action, curr_level, player_id)
    if curr_level.is_pause_on:
        return
    else:
        if curr_level.players[player_id].help_used:
            return
        elif constants.KEY_BINDINGS[action] == "pause":
            return
        else:
            game.players_old_pos[player_id] = player_old_pos
            if all(not player.is_alive
                   for player in curr_level.players.values()):
                lose(game)
                return
            if (curr_level.key == curr_level.players[player_id].pos
                    and curr_level.players[player_id].is_alive):
                curr_level.key = None
            if (curr_level.players[player_id].pos == curr_level.exit
                    and curr_level.is_key_taken
                    and curr_level.players[player_id].is_alive):
                if all(
                        player.pos == curr_level.exit
                        or not player.is_alive
                        for player in other_players.values()
                ):
                    game.turn += 1
                    win(game)
                    return
            if (curr_level.players[player_id].pos == curr_level.exit
                    and not curr_level.is_key_taken
                    and curr_level.players[player_id].is_alive):
                game.message = "Нельзя открыть дверь без ключа"
            if (curr_level.players[player_id].pos in curr_level.bonuses
                    and curr_level.players[player_id].is_alive):
                bonus = curr_level.bonuses.pop(
                    curr_level.players[player_id].pos
                )
                apply_bonus(bonus, player_id, curr_level)
                game.score += constants.SCORE_PER_BONUS
            if (game.players_old_pos[player_id]
                    != curr_level.players[player_id].pos):
                game.explored.add(game.players_old_pos[player_id])
                fog(game, player_id)
            if curr_level.players[player_id].compass_active:
                curr_level.players[player_id].compass_path = get_shortest_path(
                    curr_level.maze,
                    curr_level.players[player_id].pos,
                    curr_level.exit
                    if curr_level.key is None
                    else curr_level.key,
                    constants.BONUS_COMPASS_RANGE
                )
            is_freeze_active = curr_level.freeze_turns > 0
            alive_ids = {
                curr_id for curr_id, player in curr_level.players.items()
                if player.is_alive
            }
            if not alive_ids <= game.players_old_pos.keys():
                return
            for monster_num, monster in enumerate(monsters_in_level):
                monster_old_pos = monster.position
                monster.tick(
                    curr_level.maze,
                    curr_level.players,
                    game.turn,
                    game.rng,
                    is_freeze_active,
                    curr_level.key
                )
                for curr_id, player in curr_level.players.items():
                    if not player.is_alive:
                        continue
                    if check_collision(
                        game.players_old_pos[curr_id],
                        monster_old_pos,
                        player.pos,
                        monster.position
                    ):
                        player.is_alive = False

                curr_level.monsters[monster_num] = (
                    monster.symbol,
                    monster.position
                )
            if is_freeze_active:
                curr_level.freeze_turns -= 1
            if all(not player.is_alive
                   for player in curr_level.players.values()):
                lose(game)
                return
            game.players_old_pos.clear()
            game.turn += 1

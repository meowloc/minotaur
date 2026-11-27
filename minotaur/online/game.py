"""Преобразование сетевой карты и вызов существующей игровой логики."""

from dataclasses import asdict, dataclass, field
import random

from minotaur import constants
from minotaur.custom_types import Cell, Level, Player
from minotaur.game import GameState, check_collision, fog
from minotaur.game import move_player, step, win
from minotaur.monsters import Hunter, Wanderer, Minotaur
from minotaur.pathfinding import get_neighbors


@dataclass
class OnlineGame(GameState):
    """Игровое состояние с ID участников, уже покинувших карту."""

    escaped: list = field(default_factory=list)


def create_game(data, players, seed):
    """Создать состояние первой карты из данных хозяина.

    Args:
        data: Уже проверенная хозяином карта в формате JSON.
        players: Ники участников по ID из лобби.
        seed: Seed лобби или None.

    Returns:
        Пара из GameState и списка объектов монстров.

    Raises:
        KeyError: В данных нет нужного поля или неизвестен тип монстра.
        TypeError: Данные нельзя преобразовать в игровые объекты.
        ValueError: Неверные значения данных.
    """
    level_players = {}
    for player_id, nick in players.items():
        position = Cell(*data["players"][player_id]["pos"])
        level_players[player_id] = Player(
            pos=position, nick=nick, is_connected=True, is_ready=True)
    key = None if data["key"] is None else Cell(*data["key"])
    level = Level(
        maze=data["maze"], exit=Cell(*data["exit"]), key=key,
        players=level_players,
        monsters=[(symbol, Cell(*pos)) for symbol, pos in data["monsters"]],
        bonuses={Cell(*pos): symbol for pos, symbol in data["bonuses"]},
    )
    monster_types = {constants.HUNTER: Hunter, constants.WANDERER: Wanderer,
                     constants.MINOTAUR: Minotaur}
    monsters = [monster_types[symbol](pos) for symbol, pos in level.monsters]
    game = OnlineGame(level=level, level_num=0, rng=random.Random(seed))
    for player_id in players:
        fog(game, player_id)
    return game, monsters


def choose_first_player(game):
    """Выбрать первого игрока при запуске карты на двоих.

    Args:
        game: Игра с расставленными на карте игроками.

    Returns:
        ID случайного игрока среди тех, кто может шагнуть. Если оба
        заблокированы, любой из них может начать с пропуска хода.
    """
    level = game.level
    occupied = [player.pos for player in level.players.values()]
    candidates = []
    for player_id, player in level.players.items():
        for cell in get_neighbors(level.maze, player.pos):
            if cell not in occupied or cell == level.exit:
                candidates.append(player_id)
                break
    if not candidates:
        candidates = list(level.players)
    return game.rng.choice(candidates)


def play_turn(game, monsters, player_id, action):
    """Вызвать игровую логику с победой после выхода одного живого игрока.

    Args:
        game: Состояние текущей партии.
        monsters: Постоянные объекты монстров этой карты.
        player_id: ID живого игрока, которому разрешён ход.
        action: Игровая клавиша w, a, s, d или пробел.

    Raises:
        MovementError: Игровая логика отклонила ход.

    Вышедший остаётся в составе команды и больше не участвует в ходах.
    """
    level = game.level
    players = level.players
    player = players[player_id]
    direction = constants.KEY_BINDINGS[action]
    position = player.pos
    if direction != "wait":
        row, col = constants.DIRECTIONS[direction]
        position = Cell(position.row + row, position.col + col)
    leaving = (level.is_key_taken and position == level.exit
               and all(m.position != position for m in monsters))

    # step видит только тех, кто ещё находится на карте.
    level.players = {pid: p for pid, p in players.items()
                     if pid not in game.escaped}
    try:
        if leaving:
            level.monsters = [(m.symbol, m.position) for m in monsters]
            if direction != "wait":
                move_player(constants.DIRECTIONS[direction], player_id, level)
            fog(game, player_id)
            game.escaped.append(player_id)
            del level.players[player_id]
            active = [pid for pid, p in level.players.items() if p.is_alive]
            if not active:
                game.turn += 1
            elif active[0] in game.players_old_pos:
                # Напарник уже походил; выход завершает этот раунд.
                pid = active[0]
                other = level.players[pid]
                frozen = level.freeze_turns > 0
                for monster in monsters:
                    old = monster.position
                    monster.tick(level.maze, level.players, game.turn,
                                 game.rng, frozen, level.key)
                    if check_collision(game.players_old_pos[pid], old,
                                       other.pos, monster.position):
                        other.is_alive = False
                    if (monster.symbol == constants.MINOTAUR
                            and other.pos in monster.jump_area):
                        other.is_alive = False
                level.monsters = [(m.symbol, m.position) for m in monsters]
                if frozen:
                    level.freeze_turns -= 1
                game.players_old_pos.clear()
                game.turn += 1
        else:
            step(game, player_id, action, monsters)
    finally:
        level.players = players

    if game.escaped and all(pid in game.escaped or not p.is_alive
                            for pid, p in players.items()):
        win(game)


def game_snapshot(game, monsters, next_player_id):
    """Подготовить независимые от игры данные для game.update.

    Args:
        game: Текущее состояние игры.
        monsters: Объекты монстров, включая метки Минотавра.
        next_player_id: Следующий игрок или None после завершения уровня.

    Returns:
        Словарь с полной картой, игроками, результатом, раундом и очередью.
        Все значения поддерживают кодирование в JSON.
    """
    level = game.level
    marks = []
    for monster in monsters:
        if monster.symbol == constants.MINOTAUR:
            marks.extend(monster.mark)
    return {
        "state": game.state, "level_num": game.level_num,
        "escaped": list(game.escaped),
        "round": game.turn, "score": game.score, "message": game.message,
        "next_player_id": next_player_id, "minotaur_marks": marks,
        "level": {
            "maze": [row[:] for row in level.maze],
            "players": {key: asdict(player)
                        for key, player in level.players.items()},
            "exit": level.exit, "key": level.key,
            "monsters": [(monster.symbol, monster.position)
                         for monster in monsters],
            "bonuses": list(level.bonuses.items()),
            "freeze_turns": level.freeze_turns,
        },
    }

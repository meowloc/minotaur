"""Тесты игровой логики лабиринта."""

import pytest

from minotaur import constants
from minotaur.custom_types import Player, Level, Cell
from minotaur.exceptions import MovementError, LevelError
from minotaur.game import (
    GameState, apply_bonus, check_collision, fog, key_actions,
    lose, move_player, player_score, step, win,
)
from minotaur.monsters import Hunter, Wanderer


@pytest.fixture
def game_state():
    """Создаёт тестовый уровень с двумя игроками и монстром."""
    player_id_1 = "000001"
    player_id_2 = "000002"
    level = Level(
        maze=[
            list("#####"),
            list("#...#"),
            list("#...#"),
            list("#...#"),
            list("#####"),
        ],
        exit=Cell(3, 3),
        key=Cell(1, 3),
        players={
            player_id_1: Player(pos=Cell(1, 1)),
            player_id_2: Player(pos=Cell(1, 2)),
        },
        monsters=[(constants.HUNTER, Cell(2, 1))],
    )
    return player_id_1, level


@pytest.fixture
def move_check():
    """Создаёт тестовый уровень только с одним игроком."""
    player_id_1 = "000001"
    level = Level(
        maze=[
            list("#####"),
            list("#...#"),
            list("#...#"),
            list("#...#"),
            list("#####"),
        ],
        exit=Cell(3, 3),
        key=Cell(1, 3),
        players={player_id_1: Player(pos=Cell(2, 2))},
        monsters=[],
    )
    return player_id_1, level


@pytest.fixture
def round_state():
    """Создаёт большой лабиринт с удалёнными от игрока монстрами."""
    player_id = "000001"
    player_id_2 = "000002"
    level = Level(
        maze=[
            list("#############"),
            *[list("#...........#") for _ in range(11)],
            list("#############"),
        ],
        exit=Cell(3, 3),
        key=Cell(1, 3),
        players={
            player_id: Player(pos=Cell(1, 1)),
            player_id_2: Player(pos=Cell(1, 5)),
        },
        monsters=[
            (constants.HUNTER, Cell(11, 10)),
            (constants.WANDERER, Cell(11, 11)),
        ],
    )
    game = GameState(level=level, level_num=0)
    hunter = Hunter(position=Cell(11, 10))
    wanderer = Wanderer(position=Cell(11, 11))
    return player_id, player_id_2, game, wanderer, hunter


def test_move_right(move_check):
    """Движение направо."""
    player_id, level = move_check
    move_player((0, 1), player_id, level)
    assert level.players[player_id].pos == Cell(2, 3)
    assert level.players[player_id].steps == 1


def test_move_left(move_check):
    """Движение налево."""
    player_id, level = move_check
    move_player((0, -1), player_id, level)
    assert level.players[player_id].pos == Cell(2, 1)
    assert level.players[player_id].steps == 1


def test_move_up(move_check):
    """Движение вверх."""
    player_id, level = move_check
    move_player((-1, 0), player_id, level)
    assert level.players[player_id].pos == Cell(1, 2)
    assert level.players[player_id].steps == 1


def test_move_down(move_check):
    """Движение вниз."""
    player_id, level = move_check
    move_player((1, 0), player_id, level)
    assert level.players[player_id].pos == Cell(3, 2)
    assert level.players[player_id].steps == 1


def test_move_into_wall(game_state):
    """Нельзя попасть в клетку со стеной."""
    player_id, level = game_state
    with pytest.raises(MovementError):
        move_player((-1, 0), player_id, level)
    assert level.players[player_id].pos == Cell(1, 1)
    assert level.players[player_id].steps == 0


def test_move_into_another_player(game_state):
    """Нельзя попасть на клетку напарника вне выхода."""
    player_id, level = game_state
    with pytest.raises(MovementError):
        move_player((0, 1), player_id, level)
    assert level.players[player_id].pos == Cell(1, 1)
    assert level.players[player_id].steps == 0


def test_move_into_monster(game_state):
    """Столкновение с монстром убивает игрока."""
    player_id, level = game_state
    move_player((1, 0), player_id, level)
    assert level.players[player_id].is_alive is False
    assert level.players[player_id].pos == Cell(2, 1)


def test_unknown_bonus(game_state):
    """Неизвестный бонус вызывает ошибку."""
    player_id, level = game_state
    with pytest.raises(LevelError):
        apply_bonus("K", player_id, level)


def test_freeze_bonus(game_state):
    """Заморозка устанавливает число ходов."""
    player_id, level = game_state
    apply_bonus(constants.FREEZE, player_id, level)
    assert level.freeze_turns == constants.BONUS_FREEZE_STEPS


def test_torch_bonus(game_state):
    """Факел активируется для конкретного игрока."""
    player_id, level = game_state
    apply_bonus(constants.TORCH, player_id, level)
    assert level.players[player_id].torch_active is True


def test_compass_bonus(game_state):
    """Компас активируется для конкретного игрока."""
    player_id, level = game_state
    apply_bonus(constants.COMPASS, player_id, level)
    assert level.players[player_id].compass_active is True


def test_fog(round_state):
    """Видимые клетки запоминаются и отделяются от полутени."""
    player_id, player_id_2, game, _, _ = round_state
    game.explored = {Cell(2, 2), Cell(3, 3)}

    fog(game, player_id)

    status = game.level.players[player_id].cells_status
    assert Cell(1, 1) in status["active"]
    assert Cell(2, 1) in status["active"]
    active = set(status["active"])
    assert active <= game.explored
    assert set(status["explored"]) == game.explored - active


def test_fog_torch(round_state):
    """Факел увеличивает радиус только у владельца."""
    player_id, player_id_2, game, _, _ = round_state
    player = game.level.players[player_id]

    player.torch_active = True
    fog(game, player_id)

    assert Cell(1, 7) in player.cells_status["active"]
    assert Cell(1, 7) in game.explored


def test_key_actions_movement(move_check):
    """Клавиша движения перемещает игрока."""
    player_id, level = move_check
    key_actions("d", level, player_id)
    assert level.players[player_id].pos == Cell(2, 3)


def test_key_actions_wait(move_check):
    """Ожидание не изменяет положение игрока."""
    player_id, level = move_check
    key_actions(" ", level, player_id)
    assert level.players[player_id].pos == Cell(2, 2)
    assert level.players[player_id].steps == 0


def test_key_actions_help(move_check):
    """Помощь отмечается у игрока."""
    player_id, level = move_check
    key_actions("h", level, player_id)
    assert level.players[player_id].help_used is True


def test_key_actions_pause(move_check):
    """Пауза включается и выключается повторным нажатием."""
    player_id, level = move_check
    key_actions("p", level, player_id)
    assert level.is_pause_on is True
    key_actions("p", level, player_id)
    assert level.is_pause_on is False


def test_check_collision_same_cell():
    """Игрок и монстр оказываются в одной клетке."""
    result = check_collision(
        Cell(1, 1), Cell(2, 2), Cell(2, 2), Cell(2, 2)
    )
    assert result is True


def test_check_collision_swap():
    """Игрок и монстр меняются клетками."""
    result = check_collision(
        Cell(1, 1), Cell(1, 2), Cell(1, 2), Cell(1, 1)
    )
    assert result is True


def test_check_collision_no_collision():
    """Игрок и монстр не сталкиваются."""
    result = check_collision(
        Cell(1, 1), Cell(3, 3), Cell(1, 2), Cell(3, 2)
    )
    assert result is False


def test_win(move_check):
    """Победа начисляет очки за уровень и скорость."""
    _, level = move_check
    game = GameState(level=level, level_num=0, turn=10, score=0)
    win(game)
    expected = (constants.SCORE_PER_LEVEL
                + max(0, constants.SCORE_SPEED_BASE - 10))
    assert game.state == "Win"
    assert game.score == expected


def test_lose(move_check):
    """Поражение обнуляет общий счёт."""
    _, level = move_check
    game = GameState(level=level, level_num=0, score=150)
    lose(game)
    assert game.state == "Lose"
    assert game.score == 0


def test_player_score_alive(game_state):
    """Живой игрок получает очки."""
    player_id, level = game_state
    game = GameState(level=level, level_num=0, score=100)
    player_score(game, player_id)
    assert level.players[player_id].score == 100


def test_player_score_dead(game_state):
    """Погибший игрок не получает очки."""
    player_id, level = game_state
    level.players[player_id].is_alive = False
    game = GameState(level=level, level_num=0, score=100)
    player_score(game, player_id)
    assert level.players[player_id].score == 0


def test_step_unknown_key(round_state):
    """Неизвестная клавиша вызывает MovementError."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    with pytest.raises(MovementError):
        step(game, player_id, "x", wanderer, hunter)
    assert game.turn == 0


def test_step_paused(round_state):
    """Включение паузы не расходует игровой ход."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    step(game, player_id, "p", wanderer, hunter)
    assert game.level.is_pause_on is True
    assert game.turn == 0
    step(game, player_id, "p", wanderer, hunter)
    assert game.level.is_pause_on is False
    assert game.turn == 0


def test_step_help(round_state):
    """Вызов помощи не расходует игровой ход."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    step(game, player_id, "h", wanderer, hunter)
    assert game.level.players[player_id].help_used is True
    assert game.turn == 0


def test_step_finished_game(round_state):
    """После завершения игры новые ходы игнорируются."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.state = "Win"
    step(game, player_id, "d", wanderer, hunter)
    assert game.level.players[player_id].pos == Cell(1, 1)
    assert game.turn == 0


def test_step_dead_player(round_state):
    """Погибший игрок не может совершать ходы."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.players[player_id].is_alive = False
    step(game, player_id, "d", wanderer, hunter)
    assert game.level.players[player_id].pos == Cell(1, 1)
    assert game.turn == 0


def test_step_pick_key(round_state):
    """Игрок подбирает ключ при входе на его клетку."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.players[player_id].pos = Cell(1, 2)
    step(game, player_id, "d", wanderer, hunter)
    assert game.level.key is None
    assert game.level.is_key_taken is True


def test_step_compass(round_state):
    """Компас показывает путь к ключу."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.players[player_id].compass_active = True
    step(game, player_id, " ", wanderer, hunter)
    assert game.compass_path == [Cell(1, 2), Cell(1, 3)]
    assert len(game.compass_path) <= constants.BONUS_COMPASS_RANGE


def test_step_monsters_move(round_state):
    """Оба монстра совершают ход без заморозки."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.turn = 4
    hunter.turns_until_move = 1
    wanderer.turns_until_move = 1
    hunter_old_pos = hunter.position
    wanderer_old_pos = wanderer.position

    step(game, player_id, " ", wanderer, hunter)

    assert hunter.position != hunter_old_pos
    assert wanderer.position != wanderer_old_pos
    assert game.level.monsters == [
        (constants.HUNTER, hunter.position),
        (constants.WANDERER, wanderer.position),
    ]
    assert game.turn == 5


def test_step_freeze(round_state):
    """Бонус исчезает, а монстры стоят до конца заморозки."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.turn = 4
    hunter.turns_until_move = 1
    wanderer.turns_until_move = 1
    game.level.bonuses[Cell(1, 2)] = constants.FREEZE
    hunter_old_pos = hunter.position
    wanderer_old_pos = wanderer.position

    step(game, player_id, "d", wanderer, hunter)

    assert Cell(1, 2) not in game.level.bonuses
    assert game.score == constants.SCORE_PER_BONUS
    assert game.level.freeze_turns == constants.BONUS_FREEZE_STEPS - 1
    assert hunter.position == hunter_old_pos
    assert wanderer.position == wanderer_old_pos
    assert game.level.monsters == [
        (constants.HUNTER, hunter_old_pos),
        (constants.WANDERER, wanderer_old_pos),
    ]

    step(game, player_id, " ", wanderer, hunter)
    assert game.level.freeze_turns == constants.BONUS_FREEZE_STEPS - 2
    assert hunter.position == hunter_old_pos
    assert wanderer.position == wanderer_old_pos

    step(game, player_id, " ", wanderer, hunter)
    assert game.level.freeze_turns == 0
    assert hunter.position == hunter_old_pos
    assert wanderer.position == wanderer_old_pos

    step(game, player_id, " ", wanderer, hunter)
    assert hunter.position != hunter_old_pos
    assert wanderer.position != wanderer_old_pos
    assert game.turn == 8


def test_step_win(round_state):
    """Оба игрока на выходе завершают уровень."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.key = None
    game.level.players[player_id].pos = Cell(3, 2)
    game.level.players[player_id_2].pos = game.level.exit

    step(game, player_id, "d", wanderer, hunter)

    expected = (
        constants.SCORE_PER_LEVEL
        + max(0, constants.SCORE_SPEED_BASE - game.turn)
    )
    assert game.state == "Win"
    assert game.score == expected
    assert game.level.players[player_id].score == expected
    assert game.level.players[player_id_2].score == expected


def test_step_one_player_wins(round_state):
    """Живой игрок побеждает, если второй игрок погиб."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.key = None
    game.level.players[player_id].pos = Cell(3, 2)
    game.level.players[player_id_2].is_alive = False

    step(game, player_id, "d", wanderer, hunter)

    expected = (
        constants.SCORE_PER_LEVEL
        + max(0, constants.SCORE_SPEED_BASE - game.turn)
    )
    assert game.state == "Win"
    assert game.score == expected
    assert game.level.players[player_id].score == expected
    assert game.level.players[player_id_2].score == 0


def test_step_exit_without_key(round_state):
    """Выход без ключа недоступен."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.players[player_id].pos = Cell(3, 2)
    with pytest.raises(MovementError):
        step(game, player_id, "d", wanderer, hunter)
    assert game.state == "Round"


def test_step_lose(round_state):
    """Гибель обоих игроков завершает игру поражением."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.key = None
    hunter.position = Cell(2, 1)
    wanderer.position = Cell(2, 5)
    hunter.turns_until_move = 1
    wanderer.turns_until_move = 1

    step(game, player_id, " ", wanderer, hunter)

    assert hunter.position == Cell(1, 1)
    assert wanderer.position == Cell(1, 5)
    assert game.level.players[player_id].is_alive is False
    assert game.level.players[player_id_2].is_alive is False
    assert game.state == "Lose"
    assert game.score == 0


def test_step_one_player_dead(round_state):
    """После гибели одного игрока второй продолжает играть."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.key = None
    hunter.position = Cell(2, 1)
    hunter.turns_until_move = 1

    step(game, player_id, " ", wanderer, hunter)

    assert hunter.position == Cell(1, 1)
    assert game.level.players[player_id].is_alive is False
    assert game.level.players[player_id_2].is_alive is True
    assert game.state == "Round"
    assert game.turn == 1


def test_step_one_player_at_exit(round_state):
    """Один игрок на выходе не завершает игру за двоих."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.key = None
    game.level.players[player_id].pos = Cell(3, 2)

    step(game, player_id, "d", wanderer, hunter)

    assert game.level.players[player_id].pos == game.level.exit
    assert game.level.players[player_id_2].pos == Cell(1, 5)
    assert game.state == "Round"
    assert game.turn == 1


def test_step_second_player_finishes(round_state):
    """Второй игрок завершает уровень после первого."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.key = None
    game.level.players[player_id].pos = game.level.exit
    game.level.players[player_id_2].pos = Cell(3, 2)

    step(game, player_id_2, "d", wanderer, hunter)

    assert game.state == "Win"
    assert game.level.players[player_id].score == game.score
    assert game.level.players[player_id_2].score == game.score


def test_step_dead_player_cannot_move(round_state):
    """Погибший игрок не ходит."""
    player_id, player_id_2, game, wanderer, hunter = round_state
    game.level.players[player_id].is_alive = False
    turn_old = game.turn
    step(game, player_id, "d", wanderer, hunter)

    assert game.turn == turn_old

"""Тесты игровой логики лабиринта."""

import pytest

from minotaur import constants
from minotaur.custom_types import Player, Level, Cell
from minotaur.exceptions import MovementError, LevelError
from minotaur.game import (
    GameState, apply_bonus, check_collision, fog, key_actions,
    lose, move_player, step, win,
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
    assert set(status["discovered"]) == game.explored - active


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
    """Победа распределяет очки и обнуляет общий счёт."""
    player_id, level = move_check
    game = GameState(level=level, level_num=0, turn=10, score=20)

    win(game)

    expected = (20 + constants.SCORE_PER_LEVEL
                + max(0, constants.SCORE_SPEED_BASE - 10))
    assert game.state == "Win"
    assert game.score == 0
    assert level.players[player_id].score == expected


def test_win_without_speed_bonus(move_check):
    """При большом числе ходов бонус скорости равен нулю."""
    player_id, level = move_check
    game = GameState(level=level, level_num=0, turn=400)

    win(game)

    assert level.players[player_id].score == constants.SCORE_PER_LEVEL
    assert game.score == 0


def test_lose(move_check):
    """Поражение меняет состояние, но не начисляет очки."""
    player_id, level = move_check
    game = GameState(level=level, level_num=0, score=150)

    lose(game)

    assert game.state == "Lose"
    assert game.score == 150
    assert level.players[player_id].score == 0


def test_step_right(round_state):
    """Первый игрок двигается, но раунд ждёт второго."""
    first, second, game, wanderer, hunter = round_state
    step(game, first, "d", [hunter, wanderer])
    assert game.level.players[first].pos == Cell(1, 2)
    assert game.level.players[first].steps == 1
    assert game.players_old_pos == {first: Cell(1, 1)}
    assert Cell(1, 1) in game.explored
    assert game.turn == 0


def test_step_left(round_state):
    """Движение влево сохраняет исходную позицию."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[first].pos = Cell(2, 2)
    step(game, first, "a", [hunter, wanderer])
    assert game.level.players[first].pos == Cell(2, 1)
    assert game.players_old_pos[first] == Cell(2, 2)
    assert game.turn == 0


def test_step_up(round_state):
    """Движение вверх учитывается как действие первого игрока."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[first].pos = Cell(2, 2)
    step(game, first, "w", [hunter, wanderer])
    assert game.level.players[first].pos == Cell(1, 2)
    assert game.players_old_pos[first] == Cell(2, 2)
    assert game.turn == 0


def test_step_down(round_state):
    """Движение вниз не завершает раунд до хода напарника."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[first].pos = Cell(2, 2)
    step(game, first, "s", [hunter, wanderer])
    assert game.level.players[first].pos == Cell(3, 2)
    assert game.players_old_pos[first] == Cell(2, 2)
    assert game.turn == 0


def test_step_wait(round_state):
    """Ожидание считается действием без перемещения."""
    first, second, game, wanderer, hunter = round_state
    step(game, first, " ", [hunter, wanderer])
    assert game.level.players[first].pos == Cell(1, 1)
    assert game.players_old_pos[first] == Cell(1, 1)
    assert game.turn == 0


def test_step_unknown_key(round_state):
    """Неизвестная клавиша не записывает действие."""
    first, second, game, wanderer, hunter = round_state
    with pytest.raises(MovementError):
        step(game, first, "x", [hunter, wanderer])
    assert game.players_old_pos == {}
    assert game.turn == 0


def test_step_paused(round_state):
    """Пауза и её снятие не расходуют ход."""
    first, second, game, wanderer, hunter = round_state
    step(game, first, "p", [hunter, wanderer])
    assert game.level.is_pause_on is True
    assert game.players_old_pos == {}
    step(game, first, "p", [hunter, wanderer])
    assert game.level.is_pause_on is False
    assert game.turn == 0


def test_step_help(round_state):
    """Помощь не расходует ход."""
    first, second, game, wanderer, hunter = round_state
    step(game, first, "h", [hunter, wanderer])
    assert game.level.players[first].help_used is True
    assert game.players_old_pos == {}
    assert game.turn == 0


def test_step_finished_game(round_state):
    """После победы передвижение не выполняется."""
    first, second, game, wanderer, hunter = round_state
    game.state = "Win"
    step(game, first, "d", [hunter, wanderer])
    assert game.level.players[first].pos == Cell(1, 1)
    assert game.turn == 0


def test_step_dead_player(round_state):
    """Погибший игрок не может двигаться."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[first].is_alive = False
    step(game, first, "d", [hunter, wanderer])
    assert game.level.players[first].pos == Cell(1, 1)
    assert game.players_old_pos == {}


def test_step_pick_key(round_state):
    """Ключ подбирается сразу после входа на клетку."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[first].pos = Cell(1, 2)
    step(game, first, "d", [hunter, wanderer])
    assert game.level.key is None
    assert game.level.is_key_taken is True
    assert game.turn == 0


def test_step_compass(round_state):
    """Компас строит путь к ключу без завершения раунда."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[first].compass_active = True
    step(game, first, " ", [hunter, wanderer])
    assert game.compass_path == [Cell(1, 2), Cell(1, 3)]
    assert len(game.compass_path) <= constants.BONUS_COMPASS_RANGE


def test_step_monsters_move(round_state):
    """Монстры ходят после действий обоих живых игроков."""
    first, second, game, wanderer, hunter = round_state
    game.turn = 4
    hunter.turns_until_move = 1
    wanderer.turns_until_move = 1
    old_hunter = hunter.position
    old_wanderer = wanderer.position

    step(game, first, " ", [hunter, wanderer])
    assert hunter.position == old_hunter
    assert wanderer.position == old_wanderer
    assert game.turn == 4

    step(game, second, " ", [hunter, wanderer])
    assert hunter.position != old_hunter
    assert wanderer.position != old_wanderer
    assert game.level.monsters == [
        (constants.HUNTER, hunter.position),
        (constants.WANDERER, wanderer.position),
    ]
    assert game.players_old_pos == {}
    assert game.turn == 5


def test_step_freeze(round_state):
    """Заморозка уменьшается один раз за полный раунд."""
    first, second, game, wanderer, hunter = round_state
    game.turn = 4
    hunter.turns_until_move = 1
    wanderer.turns_until_move = 1
    game.level.bonuses[Cell(1, 2)] = constants.FREEZE
    old_hunter = hunter.position
    old_wanderer = wanderer.position

    step(game, first, "d", [hunter, wanderer])
    assert Cell(1, 2) not in game.level.bonuses
    assert game.score == constants.SCORE_PER_BONUS
    assert game.level.freeze_turns == constants.BONUS_FREEZE_STEPS

    step(game, second, " ", [hunter, wanderer])
    assert game.level.freeze_turns == constants.BONUS_FREEZE_STEPS - 1
    assert hunter.position == old_hunter
    assert wanderer.position == old_wanderer

    step(game, first, " ", [hunter, wanderer])
    step(game, second, " ", [hunter, wanderer])
    assert game.level.freeze_turns == constants.BONUS_FREEZE_STEPS - 2

    step(game, first, " ", [hunter, wanderer])
    step(game, second, " ", [hunter, wanderer])
    assert game.level.freeze_turns == 0
    assert hunter.position == old_hunter
    assert wanderer.position == old_wanderer

    step(game, first, " ", [hunter, wanderer])
    step(game, second, " ", [hunter, wanderer])
    assert hunter.position != old_hunter
    assert wanderer.position != old_wanderer
    assert game.turn == 8


def test_step_win(round_state):
    """Победа наступает сразу после достижения выхода обоими."""
    first, second, game, wanderer, hunter = round_state
    game.level.key = None
    game.level.players[first].pos = Cell(3, 2)
    game.level.players[second].pos = game.level.exit

    step(game, first, "d", [hunter, wanderer])

    expected = (constants.SCORE_PER_LEVEL
                + max(0, constants.SCORE_SPEED_BASE - game.turn))
    assert game.state == "Win"
    assert game.turn == 1
    assert game.score == 0
    assert game.level.players[first].score == expected
    assert game.level.players[second].score == expected


def test_step_one_player_wins(round_state):
    """Один живой игрок может завершить уровень."""
    first, second, game, wanderer, hunter = round_state
    game.level.key = None
    game.level.players[first].pos = Cell(3, 2)
    game.level.players[second].is_alive = False

    step(game, first, "d", [hunter, wanderer])

    expected = (constants.SCORE_PER_LEVEL
                + max(0, constants.SCORE_SPEED_BASE - game.turn))
    assert game.state == "Win"
    assert game.score == 0
    assert game.level.players[first].score == expected
    assert game.level.players[second].score == expected


def test_step_exit_without_key(round_state):
    """Попытка открыть выход без ключа расходует действие."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[first].pos = Cell(3, 2)
    step(game, first, "d", [hunter, wanderer])
    assert game.state == "Round"
    assert game.message == "Нельзя открыть дверь без ключа"
    assert game.players_old_pos[first] == Cell(3, 2)
    assert game.turn == 0


def test_step_lose(round_state):
    """После гибели обоих игроков состояние становится Lose."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[first].is_alive = False
    game.level.monsters.append((constants.HUNTER, Cell(1, 6)))
    game.level.players[second].pos = Cell(1, 5)
    step(game, second, "d", [hunter, wanderer])
    assert game.level.players[second].is_alive is False
    assert game.state == "Lose"


def test_step_one_player_dead(round_state):
    """После гибели первого игрока второй завершает раунд."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[first].is_alive = False
    step(game, second, " ", [hunter, wanderer])
    assert game.state == "Round"
    assert game.turn == 1
    assert game.players_old_pos == {}


def test_step_one_player_at_exit(round_state):
    """Выход одного игрока не завершает игру за двоих."""
    first, second, game, wanderer, hunter = round_state
    game.level.key = None
    game.level.players[first].pos = Cell(3, 2)
    step(game, first, "d", [hunter, wanderer])
    assert game.level.players[first].pos == game.level.exit
    assert game.state == "Round"
    assert game.turn == 0


def test_step_second_player_finishes(round_state):
    """Второй игрок завершает уровень после первого."""
    first, second, game, wanderer, hunter = round_state
    game.level.key = None
    game.level.players[first].pos = game.level.exit
    game.level.players[second].pos = Cell(3, 2)
    step(game, second, "d", [hunter, wanderer])
    expected = (constants.SCORE_PER_LEVEL
                + max(0, constants.SCORE_SPEED_BASE - game.turn))
    assert game.state == "Win"
    assert game.level.players[first].score == expected
    assert game.level.players[second].score == expected


def test_step_both_players_dead_cannot_move(round_state):
    """Уже погибшие игроки не могут выполнять действия."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[first].is_alive = False
    game.level.players[second].is_alive = False
    step(game, first, "d", [hunter, wanderer])
    assert game.level.players[first].pos == Cell(1, 1)
    assert game.turn == 0


def test_step_into_another_player(round_state):
    """Игрок не может пройти сквозь живого напарника."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[second].pos = Cell(1, 2)
    with pytest.raises(MovementError):
        step(game, first, "d", [hunter, wanderer])
    assert game.level.players[first].pos == Cell(1, 1)
    assert game.turn == 0


def test_step_repeated_action_ignored(round_state):
    """Повторное действие до хода напарника игнорируется."""
    first, second, game, wanderer, hunter = round_state
    step(game, first, "d", [hunter, wanderer])
    step(game, first, "d", [hunter, wanderer])
    assert game.level.players[first].pos == Cell(1, 2)
    assert game.level.players[first].steps == 1
    assert game.turn == 0


def test_step_wait_completes_round(round_state):
    """Два ожидания завершают один раунд."""
    first, second, game, wanderer, hunter = round_state
    step(game, first, " ", [hunter, wanderer])
    step(game, second, " ", [hunter, wanderer])
    assert game.turn == 1
    assert game.players_old_pos == {}


def test_step_dead_second_player_completes_round(round_state):
    """Гибель второго игрока после первого хода не блокирует раунд."""
    first, second, game, wanderer, hunter = round_state
    game.level.monsters.append((constants.HUNTER, Cell(1, 6)))
    step(game, first, " ", [hunter, wanderer])
    step(game, second, "d", [hunter, wanderer])
    assert game.level.players[second].is_alive is False
    assert game.level.players[first].is_alive is True
    assert game.turn == 1
    assert game.players_old_pos == {}


def test_step_monster_collision_same_cell(round_state):
    """Монстр убивает игрока при совпадении конечных клеток."""
    from unittest.mock import Mock

    first, second, game, wanderer, hunter = round_state
    game.level.players[second].is_alive = False
    game.level.monsters = [(constants.HUNTER, Cell(2, 1))]
    monster = Mock(position=Cell(2, 1), symbol=constants.HUNTER)

    def tick(*args):
        monster.position = Cell(1, 1)

    monster.tick.side_effect = tick
    step(game, first, " ", [monster])
    assert game.level.players[first].is_alive is False
    assert game.state == "Lose"


def test_step_into_monster_is_fatal(round_state):
    """Вход на клетку монстра убивает последнего живого игрока."""
    first, second, game, wanderer, hunter = round_state
    game.level.players[second].is_alive = False
    game.level.monsters.append((constants.HUNTER, Cell(1, 2)))

    step(game, first, "d", [hunter, wanderer])

    assert game.level.players[first].is_alive is False
    assert game.state == "Lose"

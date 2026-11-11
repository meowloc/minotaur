import pytest

from minotaur import constants
from minotaur.custom_types import Player, Level, Cell
from minotaur.exceptions import MovementError, LevelError
from minotaur.game import apply_bonus, player_move


@pytest.fixture
def game_state():
    """Создаёт тестовый уровень с двумя игроками и монстром."""
    player_1 = Player(pos=Cell(1, 1))
    player_2 = Player(pos=Cell(1, 2))
    level = Level(
            maze=[
                list("#####"),
                list("#...#"),
                list("#...#"),
                list("#...#"),
                list("#####")
            ],
            exit=Cell(3, 3),
            key=Cell(1, 3),
            players={
                "100000": player_1,
                "200000": player_2
            },
            monsters=[
                (constants.HUNTER, Cell(2, 1))
            ]
        )
    return player_1, player_2, level


@pytest.fixture
def move_check():
    """Создаёт тестовый уровень с двумя игроками и монстром."""
    player_1 = Player(pos=Cell(2, 2))
    level = Level(
        maze=[
            list("#####"),
            list("#...#"),
            list("#...#"),
            list("#...#"),
            list("#####")
        ],
        exit=Cell(3, 3),
        key=Cell(1, 3),
        players={
            "100000": player_1,
        },
        monsters=[]
        )
    return player_1, level


def test_move_left(move_check):
    """Движение налево"""
    player_1, level = move_check
    player_move((0, 1), player_1, level, None)
    assert player_1.pos == Cell(2, 3)
    assert player_1.steps == 1


def test_move_right(move_check):
    """Движение направо"""
    player_1, level = move_check
    player_move((0, -1), player_1, level, None)
    assert player_1.pos == Cell(2, 1)
    assert player_1.steps == 1


def test_move_up(move_check):
    """Движение вверх"""
    player_1, level = move_check
    player_move((-1, 0), player_1, level, None)
    assert player_1.pos == Cell(1, 2)
    assert player_1.steps == 1


def test_move_down(move_check):
    """Движение вниз"""
    player_1, level = move_check
    player_move((1, 0), player_1, level, None)
    assert player_1.pos == Cell(3, 2)
    assert player_1.steps == 1


def test_move_into_wall(game_state):
    """Нельзя попасть в клетку со стеной."""
    player_1, player_2, level = game_state
    with pytest.raises(MovementError):
        player_move((-1, 0), player_1, level, player_2)
    assert player_1.pos == Cell(1, 1)
    assert player_1.steps == 0


def test_move_into_another_player(game_state):
    """Нельзя попасть на клетку, на которой стоит твой напарник."""
    player_1, player_2, level = game_state
    with pytest.raises(MovementError):
        player_move((0, 1), player_1, level, player_2)
    assert player_1.pos == Cell(1, 1)
    assert player_1.steps == 0


def test_move_into_monster(game_state):
    """Врезался в монстра."""
    player_1, player_2, level = game_state
    player_move((1, 0), player_1, level, player_2)
    assert player_1.is_alive is False
    assert player_1.pos == Cell(2, 1)


def test_unknown_bonus(game_state):
    """Неизвестный бонус."""
    player_1, player_2, level = game_state
    with pytest.raises(LevelError):
        apply_bonus("K", player_1, level)


def test_freeze_bonus(game_state):
    """Заморозка."""
    player_1, player_2, level = game_state
    apply_bonus(constants.FREEZE, player_1, level)
    assert level.freeze_turns == constants.BONUS_FREEZE_STEPS


def test_torch_bonus(game_state):
    """Факел."""
    player_1, player_2, level = game_state
    apply_bonus(constants.TORCH, player_1, level)
    assert player_1.torch_active is True


def test_compas_bonus(game_state):
    """Компас."""
    player_1, player_2, level = game_state
    apply_bonus(constants.COMPASS, player_1, level)
    assert player_1.compass_active is True

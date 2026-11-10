import pytest

from minotaur import constants
from minotaur.custom_types import Player, Level, Cell
from minotaur.exceptions import MovementError, LevelError
from minotaur.game import apply_bonus, player_move


@pytest.fixture
def game_state():
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


def test_move_into_wall(game_state):
    """Нельзя попасть в клетку со стеной."""
    player_1, player_2, level = game_state
    with pytest.raises(MovementError):
        player_move((-1, 0), player_1, level, player_2)
        assert player_1 == Cell(1, 1)


def test_normal_move(game_state):
    """Обычный ход."""
    player_1, player_2, level = game_state
    player_move((1, 0), player_2, level, player_1)
    assert player_2.pos == Cell(2, 2)
    assert player_2.steps == 1


def test_move_into_another_player(game_state):
    """Нельзя попасть на клетку, на которой стоит твой союзник."""
    player_1, player_2, level = game_state
    with pytest.raises(MovementError):
        player_move((0, 1), player_1, level, player_2)
        assert player_1 == Cell(1, 1)


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


def test_compass_bonus(game_state):
    "Компас."
    player_1, player_2, level = game_state
    apply_bonus(constants.COMPASS, player_1, level)
    assert player_1.compass_active is True

    assert player_1.compass_active is True

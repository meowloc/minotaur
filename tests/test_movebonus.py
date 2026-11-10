import pytest

from minotaur import constants
from minotaur.custom_types import Player, Level, Cell
from minotaur.exceptions import MovementError, MinotaurError
from minotaur.pathfinding import get_bfs_distances
from minotaur.game import check_bonuses, player_move


player_1 = Player(pos = Cell(1,1))
player_2 = Player(pos = Cell(1,2))
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
        players = {
            "100000": player_1,
            "200000": player_2
        },
        monsters= [
            ("H", Cell(2, 1))
        ]
    )

def test_move_into_wall():
    """Нельзя попасть в клетку со стеной"""
    with pytest.raises(MovementError):
        player_move((-1, 0), player_1, level, player_2)
def test_move_into_another_player():
    """Врезался в Напарника"""
    with pytest.raises(MovementError):
        player_move((0, 1), player_1, level, player_2)
def test_normal_move():
    """Обычный ход"""
    player_move((1, 0), player_2, level, player_1)
    assert player_2.pos == Cell(2, 2)
    assert player_2.steps == 1

def test_move_into_monster():
    """Врезался в монстра"""
    player_move((1, 0), player_1, level, player_2)
    assert player_1.is_alive is False

def test_unknown_bonus():
    """Неизвестный бонус"""
    with pytest.raises(MinotaurError):
        check_bonuses("K", player_1, level)

def test_freeze_bonus():
    """Замарозка"""
    check_bonuses(constants.FREEZE, player_1, level)
    assert level.freeze_turns == constants.BONUS_FREEZE_STEPS
    assert  level.is_freeze_active is True
def test_torch_bonus():
    "Факел"
    check_bonuses(constants.TORCH, player_1, level)
    assert player_1.torch_active is True

def test_compass_bonus():
    "Компас"
    check_bonuses(constants.COMPASS, player_1, level)
    assert player_1.compass_active is True


import minotaur.constants as constant
import pytest
from minotaur.custom_types import *
from minotaur.exceptions import  MovementError, MinotaurError
from minotaur.pathfiding import *
from minotaur.game import *
player_1 = Player(pos = (1,1))
player_2 = Player(pos = (1,2))
level = Level(
        maze=[
            "#####",
            "#...#",
            "#...#",
            "#...#",
            "#####"
        ],
        exit=(3, 3),
        key=(1, 3),
        players = {
            "1000000": player_1,
            "2000000": player_2
        },
        monsters= [
            ("H", (2, 1))
        ]
    )

def test_move_into_wall():
    """Нельзя попасть в клетку со стеной"""
    with pytest.raises(MovementError):
        player_move((-1, 0), player_1, level)

def test_normal_move():
    """Обычный ход"""
    player_move((1, 0), player_2, level)
    assert player_2.pos == (2, 2)
    assert player_2.steps == 1
def test_move_into_another_player():
    """Врезался в Напарника"""
    with pytest.raises(MovementError):
        player_move((0, 1), player_1, level)
def test_move_into_monster():
    """Врезался в монстра"""
    player_move((1, 0), player_1, level)
    assert player_1.is_alive is False

def test_unknown_bonus():
    """Неизвестный бонус"""
    compass_path = []
    with pytest.raises(MinotaurError):
        apply_bonusses("K", player_1, level, compass_path)

def test_freeze_bonus():
    """Замарозка"""
    compass_path = []
    compass_path = apply_bonusses(constant.FREEZE, player_1, level, compass_path)
    assert level.freeze_turns == 3
def test_torch_bonus():
    "Факел"
    compass_path = []
    compass_path = apply_bonusses(constant.TORCH, player_1, level, compass_path)
    assert player_1.torch_active is True

def test_compass_key_bonus():
    "Компас до ключа"
    compass_path = []
    compass_path = apply_bonusses(constant.COMPASS, player_1, level, compass_path)
    assert player_1.compass_active is True
    assert level.key in compass_path
def test_compass_exit_bonus():
    "Компас до выхода"
    compass_path = []
    level.key = None
    compass_path = apply_bonusses(constant.COMPASS, player_1, level, compass_path)
    assert player_1.compass_active is True
    assert level.exit in compass_path
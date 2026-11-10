"""Проверки корректного уровня и совпадения координат объектов."""

import pytest

from minotaur.custom_types import Cell, Level, Player
from minotaur.exceptions import LevelError
from minotaur.levels import validate_level


def make_level():
    """Создать маленький уровень с игроком, ключом и выходом."""
    maze = [list("#####"), list("#...#"), list("#.#.#"),
            list("#...#"), list("#####")]
    return Level(maze=maze, players={"000001": Player(pos=Cell(1, 1))},
                 exit=Cell(3, 3), key=Cell(1, 3))


def test_valid_level():
    """Игрок может добраться до ключа и выхода."""
    level = make_level()
    data = validate_level(level)
    assert data["key"] == Cell(1, 3)
    assert data["exit"] == Cell(3, 3)


def test_key_on_exit():
    """Проверка отклоняет уровень, если ключ лежит на выходе."""
    level = make_level()
    level.key = level.exit
    with pytest.raises(LevelError, match="ключа и выхода совпадают"):
        validate_level(level)

import random

import pytest

from minotaur.custom_types import Cell
from minotaur.exceptions import LevelError
from minotaur.monsters import Hunter, Monster, Wanderer

mock_maze_5_rows_5_cols = [
    list("#####"),
    list("##..#"),
    list("##.##"),
    list("#..##"),
    list("#####"),
]

mock_corridor = [
    list("###########"),
    list("#.........#"),
    list("###########"),
    list("###########"),
    list("###########"),
]


def test_monster_position():
    """Монстр сохраняет переданную позицию"""
    monster = Monster(Cell(1, 1))
    assert monster.position == Cell(1, 1)


def test_monster_step_not_implemented():
    """У базового монстра метод step не реализован."""
    with pytest.raises(NotImplementedError):
        Monster(Cell(1, 2)).step(mock_maze_5_rows_5_cols, Cell(3, 1), 0,
                                 random.Random(0))


def test_hunter_steps_to_player():
    """Охотник делает шаг к игроку на своём ходу."""
    hunter = Hunter(Cell(1, 3))
    hunter.step(mock_maze_5_rows_5_cols, Cell(3, 1), 0, random.Random(0))
    assert hunter.position == Cell(1, 2)


def test_hunter_waits_on_other_turn():
    """Охотник стоит на месте, если сейчас не его ход."""
    hunter = Hunter(Cell(1, 3))
    hunter.step(mock_maze_5_rows_5_cols, Cell(3, 1), 1, random.Random(0))
    assert hunter.position == Cell(1, 3)


def test_hunter_stays_on_player():
    """Охотник на клетке игрока остаётся на месте."""
    hunter = Hunter(Cell(2, 2))
    hunter.step(mock_maze_5_rows_5_cols, Cell(2, 2), 0, random.Random(0))
    assert hunter.position == Cell(2, 2)


def test_hunter_in_wall():
    """Охотник в стене вызывает ошибку."""
    hunter = Hunter(Cell(1, 1))
    with pytest.raises(LevelError):
        hunter.step(mock_maze_5_rows_5_cols, Cell(3, 1), 0,
                    random.Random(0))


def test_wanderer_chases_near_player():
    """Бродяга рядом с игроком идёт к нему."""
    wanderer = Wanderer(Cell(1, 3))
    wanderer.step(mock_maze_5_rows_5_cols, Cell(3, 1), 0, random.Random(0))
    assert wanderer.position == Cell(1, 2)


def test_wanderer_does_not_go_back():
    """Далеко от игрока бродяга не возвращается туда, откуда пришёл."""
    wanderer = Wanderer(Cell(1, 8), previous=Cell(1, 7))
    wanderer.step(mock_corridor, Cell(1, 1), 0, random.Random(0))
    assert wanderer.position == Cell(1, 9)
    assert wanderer.previous == Cell(1, 8)


def test_wanderer_turns_back_in_dead_end():
    """В тупике бродяга возвращается назад."""
    wanderer = Wanderer(Cell(1, 9), previous=Cell(1, 8))
    wanderer.step(mock_corridor, Cell(1, 1), 0, random.Random(0))
    assert wanderer.position == Cell(1, 8)


def test_wanderer_in_wall():
    """Бродяга в стене вызывает ошибку."""
    wanderer = Wanderer(Cell(1, 1))
    with pytest.raises(LevelError):
        wanderer.step(mock_maze_5_rows_5_cols, Cell(3, 1), 0,
                      random.Random(0))

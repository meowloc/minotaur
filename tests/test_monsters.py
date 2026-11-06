
import random

import pytest

from minotaur.custom_types import Cell, Player
from minotaur.exceptions import LevelError
from minotaur.monsters import Hunter, Monster, Wanderer

mock_maze_5_rows_5_cols = [
    list("#####"),
    list("##..#"),
    list("##.##"),
    list("#..##"),
    list("#####"),
]

mock_loop = [
    list("###########"),
    list("#.........#"),
    list("#.#######.#"),
    list("#.........#"),
    list("###########"),
]

mock_corridor = [
    list("###########"),
    list("#.........#"),
    list("###########"),
    list("###########"),
    list("###########"),
]


def make_players(pos: Cell) -> dict[int, Player]:
    return {1: Player(nick="Vladimir", pos=pos)}


def test_monster_position():
    """Монстр сохраняет переданную позицию"""
    monster = Monster(Cell(1, 1))
    assert monster.position == Cell(1, 1)


def test_monster_step_not_implemented():
    """У базового монстра метод step не реализован."""
    with pytest.raises(NotImplementedError):
        Monster(Cell(1, 2))._step(mock_maze_5_rows_5_cols,
                                  make_players(Cell(3, 1)), 0,
                                  random.Random(0))


def test_hunter_steps_to_player():
    """Охотник делает шаг к игроку на своём ходу."""
    hunter = Hunter(Cell(1, 3))
    hunter.tick(mock_maze_5_rows_5_cols, make_players(Cell(3, 1)),
                0, random.Random(0), False)
    assert hunter.position == Cell(1, 2)


def test_hunter_waits_on_other_turn():
    """Охотник стоит на месте, если сейчас не его ход."""
    hunter = Hunter(Cell(1, 3))
    hunter.turns_until_move = 2
    hunter.tick(mock_maze_5_rows_5_cols, make_players(Cell(3, 1)),
                1, random.Random(0), False)
    assert hunter.position == Cell(1, 3)


def test_hunter_stays_on_player():
    """Охотник на клетке игрока остаётся на месте."""
    hunter = Hunter(Cell(2, 2))
    hunter.tick(mock_maze_5_rows_5_cols, make_players(Cell(2, 2)),
                0, random.Random(0), False)
    assert hunter.position == Cell(2, 2)


def test_hunter_in_wall():
    """Охотник в стене вызывает ошибку."""
    hunter = Hunter(Cell(1, 1))
    hunter.tick(mock_maze_5_rows_5_cols, make_players(Cell(3, 1)),
                0, random.Random(0), False)
    assert hunter.position == Cell(1, 1)


def test_wanderer_chases_near_player():
    """Бродяга рядом с игроком идёт к нему."""
    wanderer = Wanderer(Cell(1, 3))
    wanderer.tick(mock_maze_5_rows_5_cols, make_players(Cell(3, 1)),
                  0, random.Random(0), False)
    assert wanderer.position == Cell(1, 2)


def test_wanderer_does_not_go_back():
    """Далеко от игрока бродяга не возвращается туда, откуда пришёл."""
    wanderer = Wanderer(Cell(1, 8), previous=Cell(1, 7))
    wanderer.tick(mock_corridor, make_players(Cell(1, 1)),
                  0, random.Random(0), False)
    assert wanderer.position == Cell(1, 9)
    assert wanderer.previous == Cell(1, 8)


def test_wanderer_turns_back_in_dead_end():
    """В тупике бродяга возвращается назад."""
    wanderer = Wanderer(Cell(1, 9), previous=Cell(1, 8))
    wanderer.tick(mock_corridor, make_players(Cell(1, 1)),
                  0, random.Random(0), False)
    assert wanderer.position == Cell(1, 8)


def test_wanderer_in_wall():
    """Бродяга в стене вызывает ошибку."""
    wanderer = Wanderer(Cell(1, 1))
    with pytest.raises(LevelError):
        wanderer.tick(mock_maze_5_rows_5_cols, make_players(Cell(3, 1)),
                      0, random.Random(0), False)


def test_hunter_intercepts_on_way_to_key():
    """До подбора ключа охотник идёт наперерез игроку к ключу."""
    hunter = Hunter(Cell(3, 5))
    hunter.tick(mock_loop, make_players(Cell(1, 1)), 0,
                random.Random(0), False, key=Cell(1, 9))
    assert hunter.position == Cell(3, 6)


def test_hunter_chases_when_key_taken():
    """После подбора ключа охотник идёт к игроку."""
    hunter = Hunter(Cell(3, 5))
    hunter.tick(mock_loop, make_players(Cell(1, 1)), 0,
                random.Random(0), False, key=None)
    assert hunter.position == Cell(3, 4)


def test_hunter_chases_when_too_far_to_intercept():
    """Если игрок дойдёт до ключа раньше, охотник идёт к игроку."""
    hunter = Hunter(Cell(3, 5))
    hunter.tick(mock_loop, make_players(Cell(1, 1)), 0,
                random.Random(0), False, key=Cell(1, 3))
    assert hunter.position == Cell(3, 4)


def test_hunter_meets_player_as_early_as_possible():
    """Охотник выбирает ближайшую к игроку точку перехвата."""
    hunter = Hunter(Cell(1, 8))
    assert hunter._get_intercept_cell(
        mock_loop, Cell(1, 1), Cell(1, 9)) == Cell(1, 5)
    hunter.tick(mock_loop, make_players(Cell(1, 1)), 0,
                random.Random(0), False, key=Cell(1, 9))
    assert hunter.position == Cell(1, 7)

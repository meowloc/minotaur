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


def make_players(pos: Cell) -> dict[str, Player]:
    return {"000001": Player(nick="Vladimir", pos=pos)}


def test_monster_step_not_implemented():
    """У базового монстра метод step не реализован."""
    with pytest.raises(NotImplementedError):
        Monster(Cell(1, 2))._step(mock_maze_5_rows_5_cols,
                                  make_players(Cell(3, 1)), 0,
                                  random.Random(0))


@pytest.mark.parametrize("turns_until_move, is_freeze_active", [
    (2, False),
    (0, True),
])
def test_tick_skips_move(turns_until_move, is_freeze_active):
    """Монстр стоит на месте не в свой ход и во время заморозки."""
    hunter = Hunter(Cell(1, 3), turns_until_move=turns_until_move)
    hunter.tick(mock_maze_5_rows_5_cols, make_players(Cell(3, 1)),
                0, random.Random(0), is_freeze_active)
    assert hunter.position == Cell(1, 3)


@pytest.mark.parametrize("maze, start, player, expected", [
    (mock_maze_5_rows_5_cols, Cell(1, 3), Cell(3, 1), Cell(1, 2)),
    (mock_maze_5_rows_5_cols, Cell(2, 2), Cell(2, 2), Cell(2, 2)),
])
def test_hunter_chases_player(maze, start, player, expected):
    """После подбора ключа охотник идёт к игроку по кратчайшему пути
    или стоит на его клетке."""
    hunter = Hunter(start)
    hunter.tick(maze, make_players(player), 0, random.Random(0),
                False, None)
    assert hunter.position == expected


@pytest.mark.parametrize("start, key, expected", [
    (Cell(3, 5), Cell(1, 9), Cell(3, 6)),
    (Cell(1, 8), Cell(1, 9), Cell(1, 7)),
    (Cell(3, 5), Cell(1, 3), Cell(3, 4)),
])
def test_hunter_intercepts_on_way_to_key(start, key, expected):
    """Пока ключ не поднят, охотник идёт наперерез игроку к ключу,
    а если не успевает раньше игрока, идёт к самому игроку."""
    hunter = Hunter(start)
    hunter.tick(mock_loop, make_players(Cell(1, 1)), 0,
                random.Random(0), False, key)
    assert hunter.position == expected


def test_hunter_in_wall():
    """Охотник в стене не находит путь к игроку и остаётся на месте."""
    hunter = Hunter(Cell(1, 1))
    hunter.tick(mock_maze_5_rows_5_cols, make_players(Cell(3, 1)),
                0, random.Random(0), False)
    assert hunter.position == Cell(1, 1)


@pytest.mark.parametrize("maze, start, previous, player, expected", [
    (mock_maze_5_rows_5_cols, Cell(1, 3), None, Cell(3, 1), Cell(1, 2)),
    (mock_corridor, Cell(1, 8), Cell(1, 7), Cell(1, 1), Cell(1, 9)),
    (mock_corridor, Cell(1, 9), Cell(1, 8), Cell(1, 1), Cell(1, 8)),
])
def test_wanderer_step(maze, start, previous, player, expected):
    """Бродяга идёт к игроку рядом, иначе не возвращается назад,
    если только не стоит в тупике."""
    wanderer = Wanderer(start, previous=previous)
    wanderer.tick(maze, make_players(player), 0, random.Random(0), False)
    assert wanderer.position == expected
    assert wanderer.previous == start


@pytest.mark.parametrize("start, previous, expected, last_seen_after", [
    (Cell(1, 4), Cell(1, 5), Cell(1, 5), Cell(1, 7)),
    (Cell(1, 7), Cell(1, 6), Cell(1, 8), None),
])
def test_wanderer_searches_last_seen(start, previous, expected,
                                     last_seen_after):
    """Потеряв игрока, бродяга идёт туда, где видел его последний раз,
    а дойдя, забывает эту клетку и снова бродит."""
    wanderer = Wanderer(start, previous=previous, last_seen=Cell(1, 7),
                        visibility_range=1)
    wanderer.tick(mock_corridor, make_players(Cell(1, 1)), 0,
                  random.Random(0), False)
    assert wanderer.position == expected
    assert wanderer.last_seen == last_seen_after


def test_wanderer_in_wall():
    """Бродяга в стене вызывает ошибку."""
    wanderer = Wanderer(Cell(1, 1))
    with pytest.raises(LevelError):
        wanderer.tick(mock_maze_5_rows_5_cols, make_players(Cell(3, 1)),
                      0, random.Random(0), False)

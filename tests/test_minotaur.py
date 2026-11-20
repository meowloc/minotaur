"""Проверки Минотавра: прицел, прыжок, отдых и заморозка."""

import random

import pytest

from minotaur import constants
from minotaur.custom_types import Cell, Player
from minotaur.monsters import Minotaur, Phase

# Открытая комната 9 × 13, стены только по краям.
ROOM = ([list("#" * 13)]
        + [list("#" + "." * 11 + "#") for _ in range(7)]
        + [list("#" * 13)])

# Две комнаты, разделённые стеной: по коридорам не пройти.
SPLIT = [
    list("#######"),
    list("#.#.#.#"),
    list("#.#.#.#"),
    list("#######"),
]


@pytest.fixture
def minotaur():
    return Minotaur(Cell(4, 1))


def make_players(*positions, alive=True):
    return {f"00000{number}": Player(pos=pos, is_alive=alive)
            for number, pos in enumerate(positions, start=1)}


def run(minotaur, players, turns, maze=ROOM, freeze=False):
    for turn in range(turns):
        minotaur.tick(maze, players, turn, random.Random(0), freeze)


def test_aim_marks_area_around_player(minotaur):
    """Первым ходом Минотавр ставит метку 3 × 3 вокруг игрока."""
    run(minotaur, make_players(Cell(4, 5)), 1)
    assert minotaur.phase is Phase.AIM
    assert minotaur.landing == Cell(4, 5)
    assert len(minotaur.mark) == 9
    assert Cell(3, 4) in minotaur.mark and Cell(5, 6) in minotaur.mark
    assert minotaur.position == Cell(4, 1)


def test_aim_chooses_nearest_player(minotaur):
    players = make_players(Cell(4, 10), Cell(2, 3))
    run(minotaur, players, 1)
    assert minotaur.landing == Cell(2, 3)


def test_mark_skips_walls():
    """В метку попадают только проходы."""
    minotaur = Minotaur(Cell(3, 3))
    run(minotaur, make_players(Cell(1, 1)), 1)
    assert minotaur.mark == {Cell(1, 1), Cell(1, 2),
                             Cell(2, 1), Cell(2, 2)}


def test_jump_after_aim_turns(minotaur):
    """Прыжок через MINOTAUR_AIM_TURNS ходов после метки."""
    players = make_players(Cell(4, 5))
    run(minotaur, players, constants.MINOTAUR_AIM_TURNS)
    assert minotaur.position == Cell(4, 1)
    run(minotaur, players, 1)
    assert minotaur.position == Cell(4, 5)
    assert Cell(4, 5) in minotaur.jump_area
    assert minotaur.phase is Phase.REST
    assert minotaur.mark == set()


def test_player_can_leave_mark(minotaur):
    """За ходы прицела игрок успевает выйти из метки 3 × 3."""
    players = make_players(Cell(4, 5))
    run(minotaur, players, 1)
    for _ in range(constants.MINOTAUR_AIM_TURNS):
        players["000001"].pos = Cell(4, players["000001"].pos.col + 1)
        run(minotaur, players, 1)
    assert players["000001"].pos not in minotaur.jump_area


def test_jump_area_lasts_one_turn(minotaur):
    run(minotaur, make_players(Cell(4, 5)),
        constants.MINOTAUR_AIM_TURNS + 2)
    assert minotaur.jump_area == set()


def test_jump_range_is_limited(minotaur):
    """Дальняя цель: прыжок не дальше MINOTAUR_JUMP_RANGE."""
    run(minotaur, make_players(Cell(4, 11)), 1)
    assert minotaur.landing == Cell(4, 1 + constants.MINOTAUR_JUMP_RANGE)


def test_jump_over_walls():
    """Стены прыжку не мешают."""
    minotaur = Minotaur(Cell(1, 1))
    run(minotaur, make_players(Cell(1, 5)),
        constants.MINOTAUR_AIM_TURNS + 1, maze=SPLIT)
    assert minotaur.position == Cell(1, 5)


def test_rest_then_new_aim(minotaur):
    """После отдыха Минотавр снова целится."""
    players = make_players(Cell(4, 5))
    run(minotaur, players,
        constants.MINOTAUR_AIM_TURNS + 1 + constants.MINOTAUR_REST_TURNS)
    assert minotaur.phase is None
    run(minotaur, players, 1)
    assert minotaur.phase is Phase.AIM


def test_freeze_extends_rest(minotaur):
    players = make_players(Cell(4, 5))
    run(minotaur, players, constants.MINOTAUR_AIM_TURNS + 1)
    run(minotaur, players, 5, freeze=True)
    assert minotaur.phase is Phase.REST
    assert minotaur.turns_left == constants.MINOTAUR_REST_TURNS


def test_no_alive_players(minotaur):
    run(minotaur, make_players(Cell(4, 5), alive=False), 3)
    assert minotaur.phase is None
    assert minotaur.position == Cell(4, 1)

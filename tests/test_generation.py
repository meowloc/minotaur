"""Проверки построения лабиринта и открытия дополнительных проходов."""

import random

import pytest

from minotaur.custom_types import Cell
from minotaur.exceptions import GenerationError, LevelError
from minotaur.generator import add_loops, init_map_gen, making_labyrinth


def test_dfs_continues_after_exit():
    """DFS проходит через выход и открывает оставшуюся комнату."""
    maze = [
        list("#####"),
        list("#####"),
        list("#####"),
        list("#####"),
        list("#####"),
    ]
    expected = [
        list("#####"),
        list("#...#"),
        list("###.#"),
        list("#...#"),
        list("#####"),
    ]

    result = making_labyrinth(maze, Cell(1, 1), Cell(3, 3), random.Random(0))
    assert result is maze
    assert result == expected


def test_dfs_without_player_and_exit():
    """Без игрока и выхода DFS вызывает ожидаемую ошибку."""
    maze = [
        list("#####"),
        list("#####"),
        list("#####"),
        list("#####"),
        list("#####"),
    ]
    with pytest.raises(GenerationError, match="Нужны координаты"):
        making_labyrinth(maze, None, None)


def test_add_loops():
    """Одна перегородка превращается в проход; остальные клетки прежние."""
    maze = [
        list("#####"),
        list("#...#"),
        list("###.#"),
        list("#...#"),
        list("#####"),
    ]
    expected = [
        list("#####"),
        list("#...#"),
        list("#.#.#"),
        list("#...#"),
        list("#####"),
    ]
    assert add_loops(maze, 1, random.Random(0)) is maze
    assert maze == expected


def test_add_loops_not_enough_walls():
    """Если нужна пара стен, а подходит одна, карта не меняется."""
    maze = [
        list("#####"),
        list("#...#"),
        list("###.#"),
        list("#...#"),
        list("#####"),
    ]
    before = []
    for row in maze:
        before.append(row[:])
    with pytest.raises(LevelError, match="Недостаточно стен"):
        add_loops(maze, 2)
    assert maze == before


def test_init_map_gen():
    maze = init_map_gen(0)
    assert maze == [list("#########") for _ in range(7)]


def test_init_map_gen_negative_number():
    with pytest.raises(GenerationError, match="Недопустимый номер"):
        init_map_gen(-1)

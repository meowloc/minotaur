"""Прямые проверки результата трёх функций генерации."""

import random

import pytest

from minotaur import constants
from minotaur.exceptions import GenerationError, PlaceError
from minotaur.generator import init_map_gen, making_labyrinth
from minotaur.levels import place_exit_and_player


def test_init_map():
    """Первый уровень состоит только из стен и имеет заданный размер."""
    height, width = constants.LEVEL_SIZES[0]
    expected = []
    for row in range(height):
        expected.append([constants.FILE_WALL] * width)

    assert init_map_gen(0) == expected


def test_init_map_invalid_level():
    """Отрицательный индекс вызывает ошибку номера уровня."""
    with pytest.raises(GenerationError, match="Недопустимый номер уровня"):
        init_map_gen(-1)


def test_place_exit_and_player():
    """Выход и игрок стоят вдоль стен поля 7x7, центр остаётся стеной."""
    maze = [
        list("#######"),
        list("#######"),
        list("#######"),
        list("#######"),
        list("#######"),
        list("#######"),
        list("#######"),
    ]
    expected = [
        list("#######"),
        list("#####P#"),
        list("#######"),
        list("#######"),
        list("#######"),
        list("###E###"),
        list("#######"),
    ]

    positions = place_exit_and_player(maze, random.Random(0))

    assert positions == ((1, 5), (5, 3))
    assert maze == expected


def test_placement_on_occupied_map():
    """Расстановка на занятой карте вызывает ожидаемую ошибку."""
    maze = [
        list("#####"),
        list("#P###"),
        list("#####"),
        list("#####"),
        list("#####"),
    ]
    with pytest.raises(PlaceError, match="нужна карта только из стен"):
        place_exit_and_player(maze)


def test_dfs_path():
    """При seed=0 DFS прокладывает путь вправо, затем вниз к выходу."""
    maze = [
        list("#####"),
        list("#P###"),
        list("#####"),
        list("###E#"),
        list("#####"),
    ]
    expected = [
        list("#####"),
        list("#P..#"),
        list("###.#"),
        list("###E#"),
        list("#####"),
    ]

    assert making_labyrinth(maze, random.Random(0)) == expected


def test_dfs_without_player_and_exit():
    """Без игрока и выхода DFS вызывает ожидаемую ошибку."""
    maze = [
        list("#####"),
        list("#####"),
        list("#####"),
        list("#####"),
        list("#####"),
    ]
    with pytest.raises(GenerationError, match="должны быть игрок и выход"):
        making_labyrinth(maze)

"""Проверки генерации, сохранения и загрузки уровней."""

import json
import random

import pytest

from minotaur.custom_types import Cell, Level, Player
from minotaur.exceptions import LevelError, PlaceError
from minotaur.levels import generate_level, is_player_id, load_level
from minotaur.levels import place_exit_and_player, place_objects, save_level
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


def test_hex_player_id():
    assert is_player_id("5b71af")


def test_invalid_player_id():
    assert not is_player_id("5b71ag")


def test_place_exit_and_player():
    maze = [list("#####") for _ in range(5)]
    player, exit_pos = place_exit_and_player(maze, random.Random(0))
    assert {player.row, exit_pos.row} == {1, 3}
    assert {player.col, exit_pos.col} == {1, 3}


def test_place_exit_and_player_on_carved_map():
    with pytest.raises(PlaceError, match="только из стен"):
        place_exit_and_player(make_level().maze)


def test_place_objects():
    level = make_level()
    level.maze = [list("###########"), list("#.........#"),
                  list("#########.#"), list("#.........#"),
                  list("###########")]
    level.key = None
    place_objects(level, 0, random.Random(0))
    assert level.key is not None
    assert len(level.monsters) == 1
    assert len(level.bonuses) == 1


def test_place_objects_with_existing_key():
    with pytest.raises(PlaceError, match="уже содержит"):
        place_objects(make_level(), 0)


def test_generate_level_two_players():
    host = Player(pos=Cell(1, 1), nick="Max", is_connected=True)
    level = generate_level(0, random.Random(62), host, "Mira")
    assert level.players["6a0613"] is not host
    assert host.pos == Cell(1, 1)
    first = level.players["6a0613"].pos
    second = level.players["5b71af"].pos
    assert abs(first.row - second.row) + abs(first.col - second.col) == 1
    assert level.maze[second.row][second.col] == "."


def test_generate_level_host_disconnected():
    host = Player(pos=Cell(1, 1), nick="Max")
    level = generate_level(0, random.Random(0), host, "Mira")
    assert list(level.players) == ["6a0613"]


def test_generate_level_same_nickname():
    player = Player(pos=Cell(1, 1), nick="Max", is_connected=True)
    with pytest.raises(PlaceError, match="Идентификаторы игроков совпадают"):
        generate_level(0, player=player, second_nick="Max")


def test_generate_online_level_without_second_nick():
    host = Player(pos=Cell(1, 1), nick="Max", is_connected=True)
    with pytest.raises(PlaceError, match="нужен ник"):
        generate_level(0, player=host)


def test_save_level(tmp_path):
    path = tmp_path / "level.json"
    save_level(make_level(), path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["players"]["000001"]["pos"] == [1, 1]
    assert data["key"] == [1, 3]


def test_save_level_missing_directory(tmp_path):
    with pytest.raises(LevelError, match="сохранить"):
        save_level(make_level(), tmp_path / "missing" / "level.json")


def test_load_level(tmp_path):
    path = tmp_path / "level.json"
    level = make_level()
    save_level(level, path)
    assert load_level(path) == level


def test_load_level_missing_file(tmp_path):
    with pytest.raises(LevelError, match="проверить"):
        load_level(tmp_path / "missing.json")

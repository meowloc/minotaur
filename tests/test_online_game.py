"""Проверки сетевых ходов с настоящими функциями игровой логики."""

from minotaur.custom_types import Cell
from minotaur.online.server import GameServer, Session


def started_game():
    """Пройти подготовку лобби и подтвердить начальное game.update."""
    server = GameServer()
    host = Session(server)
    guest = Session(server)
    server.register(host, "6a0613", "Max")
    server.register(guest, "5b71af", "Mira")
    server.lobby_command(host, "create", {})
    server.lobby_command(guest, "join", {"lobby_id": 1})
    server.lobby_command(host, "configure", {"seed": 1})
    server.lobby_command(host, "ready", {})
    server.lobby_command(guest, "ready", {})
    server.lobby_command(host, "start", {})
    server.start_response(host, 1, 1, "prepare", {"ok": True})
    server.start_response(guest, 1, 1, "prepare", {"ok": True})
    level = {
        "maze": [list(row) for row in [
            "#######", "#.....#", "#.....#", "#.....#",
            "#.....#", "#.....#", "#######",
        ]],
        "players": {"6a0613": {"pos": [1, 1]}, "5b71af": {"pos": [1, 2]}},
        "exit": [5, 4], "key": [1, 5],
        "monsters": [["H", [5, 5]]], "bonuses": [],
    }
    assert server.lobby_command(
        host, "level", {"start_id": 1, "level": level})["ok"]
    server.start_response(host, 1, 1, "level", {"ok": True})
    server.start_response(guest, 1, 1, "level", {"ok": True})
    server.game_response(host, 1, 1, 1, {"ok": True})
    server.game_response(guest, 1, 1, 1, {"ok": True})
    first = server.sessions[server.lobbies[1]["next_player_id"]]
    second = guest if first is host else host
    return server, first, second


def test_move_and_skip():
    """Два ACK открывают ход; монстры действуют только после полного круга."""
    server, first, second = started_game()
    lobby = server.lobbies[1]
    game = lobby["game"]
    monster = lobby["monsters"][0]
    old_position = monster.position
    old_snapshot = first.game_updates[-1]

    assert server.game_command(first, "move", {"direction": "down"})["ok"]
    assert game.level.players[first.player_id].pos.row == 2
    assert old_snapshot["level"]["players"][first.player_id]["pos"].row == 1
    assert first.game_updates[-1] == second.game_updates[-1]
    assert monster.position == old_position
    assert game.turn == 0
    result = server.game_command(second, "skip", {})
    assert result["error_code"] == "UpdatePending"
    server.game_response(first, 1, 1, 2, {"ok": True})
    assert server.game_command(second, "skip", {})["error_code"] == (
        "UpdatePending")
    server.game_response(second, 1, 1, 2, {"ok": True})
    assert server.game_command(second, "skip", {})["ok"]
    assert game.turn == 1
    assert monster.position != old_position
    assert lobby["next_player_id"] == first.player_id


def test_move_errors():
    """Стена, неверное направление и чужая очередь не расходуют ход."""
    server, first, second = started_game()
    lobby = server.lobbies[1]
    position = lobby["game"].level.players[first.player_id].pos
    update_id = lobby["game_update_id"]
    assert server.game_command(second, "skip", {})["error_code"] == (
        "NotYourTurn")
    assert server.game_command(first, "move", {"direction": "up"})[
        "error_code"] == "InvalidMove"
    assert server.game_command(first, "move", {"direction": []})[
        "error_code"] == "InvalidMove"
    assert lobby["game"].level.players[first.player_id].pos == position
    assert lobby["next_player_id"] == first.player_id
    assert lobby["game_update_id"] == update_id
    assert lobby["game"].turn == 0


def test_shared_key_and_both_escape():
    """Первый ждёт на закрытом выходе; второй открывает его общим ключом."""
    server, first, second = started_game()
    lobby = server.lobbies[1]
    game = lobby["game"]
    a = game.level.players[first.player_id]
    b = game.level.players[second.player_id]
    a.pos, b.pos = Cell(5, 3), Cell(3, 4)
    game.level.key = Cell(4, 4)
    game.level.freeze_turns = 8

    def act(session, cmd, data):
        assert server.game_command(session, cmd, data)["ok"]
        for member in (first, second):
            server.game_response(member, 1, 1, lobby["game_update_id"],
                                 {"ok": True})

    act(first, "move", {"direction": "right"})
    assert a.pos == game.level.exit and not game.escaped
    act(second, "move", {"direction": "down"})
    assert game.level.key is None
    act(first, "skip", {})
    assert game.escaped == [first.player_id] and game.state == "Round"
    assert lobby["next_player_id"] == second.player_id
    act(second, "move", {"direction": "down"})
    assert game.state == "Win" and a.score > 0 and b.score > 0


def test_one_escapes_partner_dies():
    """Гибель второго после выхода первого сохраняет победу и старые очки."""
    server, first, second = started_game()
    lobby = server.lobbies[1]
    game = lobby["game"]
    game.level.key = None
    a = game.level.players[first.player_id]
    b = game.level.players[second.player_id]
    a.pos, b.pos = Cell(5, 3), Cell(4, 5)
    b.score = 75
    assert server.game_command(first, "move", {"direction": "right"})["ok"]
    assert game.state == "Round"
    for member in (first, second):
        server.game_response(member, 1, 1, 2, {"ok": True})
    assert server.game_command(second, "move", {"direction": "down"})["ok"]
    assert game.state == "Win" and a.is_alive and not b.is_alive
    assert a.score > 0 and b.score == 75
    assert game.score == a.score + 75
    assert second.game_updates[-1]["next_player_id"] is None


def test_death_and_return_to_lobby():
    """Шаг на монстра убивает; поражение возвращает обоих в то же лобби."""
    server, first, second = started_game()
    lobby = server.lobbies[1]
    game = lobby["game"]
    game.level.players[second.player_id].is_alive = False
    player = game.level.players[first.player_id]
    lobby["monsters"][0].position = Cell(player.pos.row + 1, player.pos.col)

    assert server.game_command(first, "move", {"direction": "down"})["ok"]
    assert not player.is_alive
    assert first.game_updates[-1]["state"] == "Lose"
    server.game_response(first, 1, 1, 2, {"ok": True})
    server.game_response(second, 1, 1, 2, {"ok": True})
    assert lobby["state"] == "waiting"
    assert lobby["level"] is None
    assert lobby["game"] is None
    assert not any(lobby["ready"].values())
    assert first.lobby_id == second.lobby_id == 1


def test_old_ack_and_rejected_update():
    """Старый ACK игнорируется; sync повторяет карту после отказа."""
    server, first, second = started_game()
    lobby = server.lobbies[1]
    server.game_command(first, "skip", {})
    server.game_response(first, 1, 1, 1, {"ok": True})
    assert len(lobby["game_waiting"]) == 2
    server.game_response(second, 1, 1, 2, {"ok": False})
    assert not second.finished
    assert second.player_id in lobby["game_waiting"]
    assert server.game_command(first, "skip", {})["error_code"] == (
        "UpdatePending")
    assert server.game_command(second, "sync", {})["ok"]
    assert second.game_updates[-1]["update_id"] == 2
    for member in (first, second):
        server.game_response(member, 1, 1, 2, {"ok": True})
    assert server.game_command(second, "skip", {})["ok"]


def test_survivor_plays_each_round():
    """Живой ходит каждый раунд, погибший продолжает получать обновления."""
    server, first, second = started_game()
    lobby = server.lobbies[1]
    game = lobby["game"]
    game.level.players[second.player_id].is_alive = False
    assert server.game_command(first, "skip", {})["ok"]
    assert game.turn == 1
    assert lobby["next_player_id"] == first.player_id
    assert first.game_updates[-1] == second.game_updates[-1]
    server.game_response(first, 1, 1, 2, {"ok": True})
    server.game_response(second, 1, 1, 2, {"ok": True})
    assert server.game_command(second, "skip", {})["error_code"] == (
        "PlayerDead")


def test_chat_pause_on_disconnect():
    """Выход из партии сообщает о паузе, новый игрок видит её в истории."""
    server, host, guest = started_game()

    old_id = guest.player_id
    old_nick = server.players[old_id]
    guest.unregister()
    assert server.lobbies[1]["state"] == "paused"
    cmd, data = host.chat_updates[-1]
    assert cmd == "recv"
    assert data["lobby_id"] == 1
    assert data["message"]["from"] is None
    assert data["message"]["message"] == (
        "Партия на паузе: ждём второго игрока.")
    assert guest.chat_updates == []

    server.register(guest, old_id, old_nick)
    server.lobby_command(guest, "join", {"lobby_id": 1})
    assert guest.chat_updates[0][0] == "history"
    assert guest.chat_updates[0][1]["messages"][-1] == data["message"]
    assert server.lobbies[1]["state"] == "paused"
    update = guest.game_updates[-1]
    server.game_response(host, 1, 1, update["update_id"], {"ok": True})
    assert server.lobbies[1]["state"] == "paused"
    server.game_response(guest, 1, 1, update["update_id"], {"ok": True})
    assert server.lobbies[1]["state"] == "started"


def test_replace_player_mid_round():
    """Замена после хода сохраняет позицию и не даёт ходить второй раз."""
    server, first, second = started_game()
    lobby = server.lobbies[1]
    game = lobby["game"]
    old_id = first.player_id
    player = game.level.players[old_id]
    player.score = 75
    assert server.game_command(first, "move", {"direction": "down"})["ok"]
    position = player.pos
    old_update = lobby["game_update_id"]
    server.lobby_command(first, "leave", {})

    new = Session(server)
    server.register(new, "111111", "Alex")
    assert server.lobby_command(new, "join", {"lobby_id": 1})["ok"]
    update = new.game_updates[-1]
    assert update == second.game_updates[-1]
    assert old_id not in update["level"]["players"]
    assert update["level"]["players"]["111111"]["pos"] == position
    assert update["level"]["players"]["111111"]["score"] == 75
    assert "111111" in game.players_old_pos
    assert server.game_command(second, "skip", {})["ok"] is False
    server.game_response(second, 1, 1, old_update, {"ok": True})
    assert len(lobby["game_waiting"]) == 2
    for member in (new, second):
        server.game_response(member, 1, 1, update["update_id"], {"ok": True})
    assert server.game_command(second, "skip", {})["ok"]
    assert game.turn == 1
    assert lobby["next_player_id"] == "111111"

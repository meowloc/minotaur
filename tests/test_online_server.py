"""Успешные и ошибочные случаи регистрации и команд сервера."""

from minotaur.online.server import GameServer, Session


def test_register():
    """Свободный ID добавляется в словари игроков и сессий."""
    server = GameServer()
    session = Session(server)

    assert server.register(session, "6a0613", "Max") is True
    assert server.players == {"6a0613": "Max"}
    assert server.sessions == {"6a0613": session}
    assert session.player_id == "6a0613"


def test_register_duplicate():
    """Второй клиент с занятым ID получает отказ."""
    server = GameServer()
    first = Session(server)
    second = Session(server)
    server.register(first, "6a0613", "Max")

    assert server.register(second, "6a0613", "Max") is False
    assert server.sessions["6a0613"] is first
    assert second.player_id is None


def test_handle_request():
    """hello регистрирует игрока, disconnect освобождает его ID."""
    server = GameServer()
    session = Session(server)
    packet = {"num": 1, "type": "req", "topic": "system",
              "cmdid": "hello", "id": "6a0613", "data": {"nick": "Max"}}

    assert session.handle_request(packet) == ("hello", {"ok": True})
    assert session.player_id == "6a0613"

    packet["num"] = 2
    packet["cmdid"] = "disconnect"
    packet["data"] = {}
    assert session.handle_request(packet) == ("disconnect", {"ok": True})
    assert session.finished is True
    assert server.players == {}
    assert server.sessions == {}


def test_handle_request_wrong_id():
    """hello с ID, который не соответствует нику, получает отказ."""
    server = GameServer()
    session = Session(server)
    packet = {"num": 1, "type": "req", "topic": "system",
              "cmdid": "hello", "id": "000000", "data": {"nick": "Max"}}

    cmd, data = session.handle_request(packet)
    assert cmd == "hello"
    assert data["ok"] is False
    assert data["error_code"] == "InvalidPlayerId"
    assert server.players == {}


def test_lobby_command():
    """Оба игрока получают update, при выходе хозяина права переходят гостю."""
    server = GameServer()
    host = Session(server)
    guest = Session(server)
    server.register(host, "6a0613", "Max")
    server.register(guest, "5b71af", "Mira")

    created = server.lobby_command(host, "create", {})
    lobby_id = created["lobby"]["lobby_id"]
    assert created["ok"] is True
    joined = server.lobby_command(guest, "join", {"lobby_id": lobby_id})
    assert joined["ok"] is True

    assert server.lobby_command(host, "update", {}) == {"ok": True}
    assert host.updates[-1] == joined["lobby"]
    assert guest.updates[-1] == joined["lobby"]

    assert server.lobby_command(host, "leave", {}) == {"ok": True}
    assert guest.updates[-1]["host_id"] == "5b71af"
    assert guest.updates[-1]["players"] == {"5b71af": "Mira"}
    assert host.lobby_id is None
    assert host.updates == []

    assert server.lobby_command(guest, "leave", {}) == {"ok": True}
    assert server.lobby_command(guest, "list", {})["lobbies"] == []


def test_lobby_command_without_lobby():
    """update вне лобби получает отказ и не создаёт обновлений."""
    server = GameServer()
    session = Session(server)
    server.register(session, "6a0613", "Max")

    result = server.lobby_command(session, "update", {})
    assert result["ok"] is False
    assert result["error_code"] == "NotInLobby"
    assert session.updates == []

"""Подготовка двух игроков, передача карты и отмена запуска."""

from minotaur.online.server import GameServer, Session


def ready_lobby():
    """Создать сервер с двумя готовыми игроками для проверок запуска."""
    server = GameServer()
    host = Session(server)
    guest = Session(server)
    server.register(host, "6a0613", "Max")
    server.register(guest, "5b71af", "Mira")
    server.lobby_command(host, "create", {})
    server.lobby_command(guest, "join", {"lobby_id": 1})
    server.lobby_command(host, "ready", {})
    server.lobby_command(guest, "ready", {})
    return server, host, guest


def test_start():
    """Игра начинается только после подготовки и получения карты обоими."""
    server, host, guest = ready_lobby()
    result = server.lobby_command(host, "start", {})
    assert result == {"ok": True, "start_id": 1}
    assert host.start_updates[-1] == (
        "prepare", {"lobby_id": 1, "start_id": 1})
    assert guest.start_updates[-1] == host.start_updates[-1]

    server.start_response(host, 1, 1, "prepare", {"ok": True})
    assert server.lobbies[1]["state"] == "preparing"
    server.start_response(guest, 1, 1, "prepare", {"ok": True})
    assert server.lobbies[1]["state"] == "generating"
    assert host.start_updates[-1][0] == "generate"
    assert guest.start_updates[-1][0] == "prepare"
    server.start_response(host, 1, 1, "generate", {"ok": True})

    level = {
        "maze": [list(row) for row in
                 ["#######", "#.....#", "#.....#", "#.....#", "#######"]],
        "players": {"6a0613": {"pos": [1, 1]}, "5b71af": {"pos": [1, 2]}},
        "exit": [3, 5], "key": [1, 5],
        "monsters": [["H", [3, 1]]], "bonuses": [],
    }
    result = server.lobby_command(
        host, "level", {"start_id": 1, "level": level})
    assert result == {"ok": True}
    assert host.start_updates[-1][1]["level"] == level
    assert guest.start_updates[-1] == host.start_updates[-1]
    server.start_response(host, 1, 1, "level", {"ok": True})
    assert server.lobbies[1]["state"] == "loading"
    server.start_response(guest, 1, 1, "level", {"ok": True})
    assert server.lobbies[1]["state"] == "started"
    assert host.updates[-1] == guest.updates[-1]
    assert "level" not in host.updates[-1]
    assert host.chat_updates[-1][1]["message"]["message"] == "Партия началась."


def test_start_refused():
    """Старт требует хозяина и двух готовых, после старта настройки закрыты."""
    server, host, guest = ready_lobby()
    result = server.lobby_command(guest, "start", {})
    assert result["error_code"] == "HostRequired"
    server.lobby_command(guest, "unready", {})
    result = server.lobby_command(host, "start", {})
    assert result["error_code"] == "CannotStart"
    assert host.start_updates == []

    server.lobby_command(guest, "ready", {})
    server.lobby_command(host, "start", {})
    result = server.lobby_command(guest, "unready", {})
    assert result["error_code"] == "LobbyLocked"
    result = server.lobby_command(host, "configure", {"seed": 42})
    assert result["error_code"] == "LobbyLocked"
    result = server.lobby_command(host, "start", {})
    assert result["error_code"] == "CannotStart"


def test_start_bad_level():
    """Неверная карта отменяет запуск, сообщение об ошибке генерации тоже."""
    server, host, guest = ready_lobby()
    server.lobby_command(host, "start", {})
    server.start_response(host, 1, 1, "prepare", {"ok": True})
    server.start_response(guest, 1, 1, "prepare", {"ok": True})
    result = server.lobby_command(host, "level", {"start_id": 1, "level": {}})
    assert result["error_code"] == "InvalidLevel"
    assert server.lobbies[1]["state"] == "waiting"
    assert host.start_updates == guest.start_updates == []

    server.lobby_command(host, "start", {})
    server.start_response(host, 1, 2, "prepare", {"ok": True})
    server.start_response(guest, 1, 2, "prepare", {"ok": True})
    result = server.lobby_command(host, "level", {"start_id": 2, "ok": False})
    assert result == {"ok": True}
    assert server.lobbies[1]["state"] == "waiting"
    assert server.lobbies[1]["level"] is None


def test_start_cancelled():
    """Отказ или выход отменяет подготовку, старый ACK не запускает новую."""
    server, host, guest = ready_lobby()
    server.lobby_command(host, "start", {})
    server.start_response(guest, 1, 1, "prepare", {"ok": False})
    assert server.lobbies[1]["state"] == "waiting"
    server.lobby_command(host, "start", {})
    server.start_response(guest, 1, 1, "prepare", {"ok": True})
    assert server.lobbies[1]["confirmed"] == []
    result = server.lobby_command(host, "level", {"start_id": 1, "level": {}})
    assert result["error_code"] == "UnexpectedLevel"

    guest.unregister()
    assert server.lobbies[1]["state"] == "waiting"
    assert server.lobbies[1]["players"] == {"6a0613": "Max"}
    assert host.updates[-1]["can_start"] is False
    assert host.start_updates == []

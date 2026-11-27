"""Проверки настроек лобби и готовности игроков."""

from minotaur.online.server import GameServer, Session


def test_configure():
    """Хозяин меняет настройки, оба игрока получают состояние и сообщение."""
    server = GameServer()
    host = Session(server)
    guest = Session(server)
    server.register(host, "6a0613", "Max")
    server.register(guest, "5b71af", "Mira")
    server.lobby_command(host, "create", {})
    server.lobby_command(guest, "join", {"lobby_id": 1})

    result = server.lobby_command(
        host, "configure", {"name": "Наше лобби", "seed": 42})
    assert result == {"ok": True}
    assert host.updates[-1]["name"] == "Наше лобби"
    assert host.updates[-1]["seed"] == 42
    assert guest.updates[-1] == host.updates[-1]
    assert host.chat_updates[-1] == guest.chat_updates[-1]
    assert host.chat_updates[-1][1]["message"]["from"] is None


def test_configure_errors():
    """Гость получает отказ, неверный seed не меняет даже допустимое имя."""
    server = GameServer()
    host = Session(server)
    guest = Session(server)
    server.register(host, "6a0613", "Max")
    server.register(guest, "5b71af", "Mira")
    server.lobby_command(host, "create", {})
    server.lobby_command(guest, "join", {"lobby_id": 1})

    result = server.lobby_command(guest, "configure", {"name": "Другое"})
    assert result["ok"] is False
    assert result["error_code"] == "HostRequired"
    result = server.lobby_command(
        host, "configure", {"name": "Другое", "seed": "ошибка"})
    assert result["error_code"] == "InvalidSeed"
    assert server.lobbies[1]["name"] == "Max"
    assert server.lobbies[1]["seed"] is None


def test_ready_and_unready():
    """Двое готовы: старт доступен. Выход и unready отменяют доступность."""
    server = GameServer()
    host = Session(server)
    guest = Session(server)
    server.register(host, "6a0613", "Max")
    server.register(guest, "5b71af", "Mira")
    server.lobby_command(host, "create", {})
    server.lobby_command(host, "ready", {})
    assert host.updates[-1]["can_start"] is False
    server.lobby_command(guest, "join", {"lobby_id": 1})
    assert host.updates[-1]["ready"]["5b71af"] is False

    assert server.lobby_command(guest, "ready", {}) == {"ok": True}
    ready_state = host.updates[-1]
    assert ready_state["can_start"] is True
    assert guest.updates[-1] == ready_state
    assert server.lobby_command(guest, "unready", {}) == {"ok": True}
    assert host.updates[-1]["can_start"] is False
    assert ready_state["ready"]["5b71af"] is True

    server.lobby_command(guest, "ready", {})
    server.lobby_command(host, "leave", {})
    assert guest.updates[-1]["can_start"] is False
    assert guest.updates[-1]["ready"] == {"5b71af": True}
    assert server.lobby_command(guest, "configure", {"seed": 10})["ok"]


def test_ready_without_lobby():
    """Готовность доступна только участнику лобби."""
    server = GameServer()
    session = Session(server)
    server.register(session, "6a0613", "Max")

    result = server.lobby_command(session, "ready", {})
    assert result["ok"] is False
    assert result["error_code"] == "NotInLobby"
    assert session.updates == []
    assert session.chat_updates == []

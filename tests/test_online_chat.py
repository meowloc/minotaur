"""Проверки чата, истории и повторной доставки запросов."""

from pwn import listen, remote

from minotaur.online.protocol import Protocol, encode_packet, read_packet
from minotaur.online.server import GameServer, Session


def test_chat_send():
    """Сообщение получает своё лобби, соседнее лобби остаётся без сообщений."""
    server = GameServer()
    host = Session(server)
    guest = Session(server)
    stranger = Session(server)
    server.register(host, "6a0613", "Max")
    server.register(guest, "5b71af", "Mira")
    server.register(stranger, "000001", "Другой")
    server.lobby_command(host, "create", {})
    server.lobby_command(stranger, "create", {})
    server.lobby_command(guest, "join", {"lobby_id": 1})

    result = server.chat_command(host, "send", {"message": "Привет"})
    assert result == {"ok": True, "message_id": 2}
    cmd, data = guest.chat_updates[-1]
    assert cmd == "recv"
    assert data == {"lobby_id": 1, "message": {
        "message_id": 2, "from": "6a0613", "message": "Привет",
    }}
    assert host.chat_updates[-1] == guest.chat_updates[-1]
    assert stranger.chat_updates == []
    assert server.histories[2] == []


def test_chat_errors():
    """Вне лобби отправка запрещена, пустое сообщение тоже отклоняется."""
    server = GameServer()
    session = Session(server)
    server.register(session, "6a0613", "Max")

    result = server.chat_command(session, "send", {"message": "Привет"})
    assert result["ok"] is False
    assert result["error_code"] == "NotInLobby"

    server.lobby_command(session, "create", {})
    result = server.chat_command(session, "send", {"message": "   "})
    assert result["ok"] is False
    assert result["error_code"] == "InvalidMessage"
    assert server.histories[1] == []
    assert session.chat_updates == []


def test_chat_history():
    """Гость получает прошлые сообщения, выход записывается в историю."""
    server = GameServer()
    host = Session(server)
    guest = Session(server)
    server.register(host, "6a0613", "Max")
    server.register(guest, "5b71af", "Mira")
    server.lobby_command(host, "create", {})
    server.chat_command(host, "send", {"message": "Жду второго игрока"})
    history = server.chat_command(host, "history", {})

    server.lobby_command(guest, "join", {"lobby_id": 1})
    cmd, data = guest.chat_updates[0]
    assert cmd == "history"
    assert data["messages"] == history["messages"]
    assert len(data["messages"]) == 1
    assert guest.chat_updates[1][1]["message"]["from"] is None

    server.lobby_command(guest, "leave", {})
    assert guest.chat_updates == []
    assert server.histories[1][-1]["message"] == "Игрок Mira вышел из лобби."
    server.lobby_command(host, "leave", {})
    assert server.histories == {}


def test_chat_repeated_request():
    """Повтор send получает прежний ответ и сохраняется в истории один раз."""
    server = GameServer()
    session = Session(server)
    server.register(session, "6a0613", "Max")
    server.lobby_command(session, "create", {})
    packet = {"num": 1, "type": "req", "topic": "chat", "cmdid": "send",
              "id": "6a0613", "data": {"message": "Привет"}}

    with listen(0, bindaddr="127.0.0.1", fam="ipv4") as listener:
        with remote("127.0.0.1", listener.lport) as client:
            protocol = Protocol(listener.wait_for_connection())
            client.sendline(encode_packet(packet))
            protocol.receive(session.handle_request)
            first = read_packet(client, 1)
            client.sendline(encode_packet(packet))
            protocol.receive(session.handle_request)
            assert read_packet(client, 1) == first
            assert first["data"] == {"ok": True, "message_id": 1}
    assert len(server.histories[1]) == 1
    assert len(session.chat_updates) == 1

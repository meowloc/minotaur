"""Проверки регистрации, выхода и команд лобби игрового сервера."""

import subprocess
import sys
from threading import Thread

import pytest
from pwn import listen, remote

from minotaur.online.protocol import encode_packet, read_packet
from minotaur.online.server import GameServer


def request(client, num, topic, cmd, player_id, data):
    """Отправить один запрос и проверить, что пришёл ответ именно на него."""
    packet = dict(num=num, type="req", topic=topic, cmdid=cmd,
                  id=player_id, data=data)
    client.sendline(encode_packet(packet))
    reply = read_packet(client, 2)
    assert reply is not None
    result = reply["data"]
    assert reply == dict(packet, type="resp", data=result)
    return result


@pytest.fixture
def port():
    """Запустить сервер на свободном порту на время теста."""
    process = subprocess.Popen(
        [sys.executable, "-X", "utf8", "main_server.py", "--port", "0"],
        stdout=subprocess.PIPE, encoding="utf-8",
    )
    try:
        for line in process.stdout:
            if line.startswith("Сервер слушает порт "):
                break
        else:
            pytest.fail("Сервер завершился до открытия порта.")
        yield int(line.split()[-1])
    finally:
        process.terminate()
        process.wait(timeout=5)
        process.stdout.close()


def test_hello_required(port):
    """Проверка доступности не требует регистрации, а список лобби требует."""
    remote("127.0.0.1", port).close()
    with remote("127.0.0.1", port) as client:
        denied = request(client, 1, "lobby", "list", "6a0613", {})
        assert denied == {"ok": False, "error": "Сначала отправьте hello."}
        denied = request(client, 2, "system", "hello", "6a0613", {"nick": "X"})
        assert denied["ok"] is False


def test_server_connections(port):
    """Два игрока входят, выходят и могут занять освободившийся ID."""
    max_id = "6a0613"
    mira_id = "5b71af"
    max_nick = {"nick": "Max"}
    mira_nick = {"nick": "Mira"}
    ok = {"ok": True}
    host = "127.0.0.1"
    with remote(host, port) as first, remote(host, port) as second:
        assert request(first, 1, "system", "hello", max_id, max_nick) == ok
        denied = request(second, 1, "system", "hello", max_id, max_nick)
        assert denied["ok"] is False
        assert request(second, 2, "system", "hello", mira_id, mira_nick) == ok
        denied = request(first, 2, "system", "disconnect", mira_id, {})
        assert denied["ok"] is False
        assert request(first, 3, "system", "disconnect", max_id, {}) == ok
        with pytest.raises(EOFError):
            first.recv(1, timeout=2)
        with remote("127.0.0.1", port) as again:
            assert request(again, 1, "system", "hello", max_id, max_nick) == ok
        assert request(second, 3, "system", "disconnect", mira_id, {}) == ok


def test_connection_lost():
    """Обрыв без disconnect освобождает ник и сеанс зарегистрированного ID."""
    game = GameServer()
    with listen(0, bindaddr="127.0.0.1", fam="ipv4") as listener:
        with remote("127.0.0.1", listener.lport) as client:
            tube = listener.wait_for_connection()
            worker = Thread(target=game.serve_client, args=(tube,),
                            daemon=True)
            worker.start()
            request(client, 1, "system", "hello", "6a0613", {"nick": "Max"})
            assert game.players == {"6a0613": "Max"}
            assert game.sessions["6a0613"].player_id == "6a0613"
        worker.join(timeout=2)
        assert not worker.is_alive()
        assert game.players == {}
        assert game.sessions == {}


def receive_update(client, player_id):
    """Прочитать обновление состава, подтвердить его и вернуть данные лобби."""
    seen = getattr(client, "seen_updates", set())
    client.seen_updates = seen
    while True:
        packet = read_packet(client, 3)
        assert packet["type"] == "req"
        assert packet["topic"] == "lobby"
        assert packet["cmdid"] == "update"
        assert packet["id"] == player_id
        ack = dict(packet, type="resp", data={"ok": True})
        client.sendline(encode_packet(ack))
        if packet["num"] not in seen:
            seen.add(packet["num"])
            return packet["data"]["lobby"]


@pytest.mark.parametrize("lost_connection", [False, True])
def test_lobby(port, lost_connection):
    """После выхода или обрыва связи хозяина второй игрок получает лобби."""
    host_id, guest_id = "6a0613", "5b71af"
    with remote("127.0.0.1", port) as host, remote("127.0.0.1", port) as guest:
        request(host, 1, "system", "hello", host_id, {"nick": "Max"})
        request(guest, 1, "system", "hello", guest_id, {"nick": "Mira"})
        denied = request(guest, 6, "lobby", "update", guest_id, {})
        assert denied == {"ok": False, "error": "Вы не в лобби."}
        lobby = request(host, 2, "lobby", "create", host_id, {})["lobby"]
        assert lobby == dict(lobby_id=1, name="Max", host_id=host_id,
                             players={host_id: "Max"})
        listed = request(guest, 2, "lobby", "list", guest_id, {})
        assert listed["lobbies"] == [lobby]
        target = {"lobby_id": 1}
        joined = request(guest, 3, "lobby", "join", guest_id, target)["lobby"]
        assert joined["players"] == {host_id: "Max", guest_id: "Mira"}
        assert receive_update(host, host_id) == joined
        assert request(host, 7, "lobby", "update", host_id, {}) == {"ok": True}
        assert receive_update(host, host_id) == joined
        assert receive_update(guest, guest_id) == joined
        if lost_connection:
            host.close()
        else:
            assert request(host, 3, "lobby", "leave", host_id, {})["ok"]
        remaining = receive_update(guest, guest_id)
        assert remaining["host_id"] == guest_id
        assert remaining["players"] == {guest_id: "Mira"}
        assert request(guest, 4, "lobby", "leave", guest_id, {})["ok"]
        listed = request(guest, 5, "lobby", "list", guest_id, {})
        assert listed["lobbies"] == []

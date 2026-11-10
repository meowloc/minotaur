"""Основные проверки сетевого протокола."""

import pytest
from pwn import listen, remote

from minotaur.online.protocol import Protocol, encode_packet, read_packet


def test_request():
    """На ping приходит pong. Байты в данных запроса вызывают TypeError."""
    def pong(packet):
        return "pong", {"ok": True}

    with listen(0, bindaddr="127.0.0.1", fam="ipv4") as server:
        with remote("127.0.0.1", server.lport) as connection:
            client = Protocol(connection)
            num = client.request("system", "ping", "000042", {})
            protocol = Protocol(server.wait_for_connection())
            protocol.receive(pong)
            reply = client.receive(pong)

            assert reply == {"num": num, "type": "resp", "topic": "system",
                             "cmdid": "pong", "id": "000042",
                             "data": {"ok": True}}

            with pytest.raises(TypeError):
                client.request("chat", "send", "000042", {"message": b"hi"})


def test_read_packet():
    """Полный пакет читается, а пустой JSON-объект вызывает ошибку."""
    ping = {"num": 1, "type": "req", "topic": "system", "cmdid": "ping",
            "id": "000042", "data": {}}
    with listen(0, bindaddr="127.0.0.1", fam="ipv4") as server:
        with remote("127.0.0.1", server.lport) as client:
            connection = server.wait_for_connection()
            client.sendline(encode_packet(ping))
            assert read_packet(connection, 1) == ping

            client.sendline(b"{}")
            with pytest.raises(ValueError, match="Нужны поля"):
                read_packet(connection, 1)


def test_receive():
    """Повтор получает прежний ACK; другой запрос с тем же номером отклонён."""
    messages = []

    def save_message(packet):
        messages.append(packet["data"]["message"])
        return "recv", {"ok": True}

    request = {"num": 1, "type": "req", "topic": "chat", "cmdid": "send",
               "id": "000042", "data": {"message": "Привет"}}
    with listen(0, bindaddr="127.0.0.1", fam="ipv4") as server:
        with remote("127.0.0.1", server.lport) as client:
            protocol = Protocol(server.wait_for_connection())
            client.sendline(encode_packet(request))
            protocol.receive(save_message)
            first_ack = read_packet(client, 1)

            client.sendline(encode_packet(request))
            protocol.receive(save_message)
            second_ack = read_packet(client, 1)

            assert messages == ["Привет"]
            assert first_ack["data"] == {"ok": True}
            assert second_ack == first_ack

            request["data"]["message"] = "Пока"
            client.sendline(encode_packet(request))
            with pytest.raises(ValueError, match="номер уже занят"):
                protocol.receive(save_message)
            assert messages == ["Привет"]

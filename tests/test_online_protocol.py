"""Основные проверки сетевого протокола."""

from pwn import listen, remote

from minotaur.online.protocol import Protocol, encode_packet, read_packet


def test_ping():
    """На ping приходит pong с тем же номером и ID игрока."""
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


def test_same_request_twice():
    """На два одинаковых запроса выдаются два ACK, а сообщение в чате одно."""
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

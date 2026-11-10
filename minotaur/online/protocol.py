"""Обмен JSON по одному соединению pwntools. Один пакет занимает строку."""

import json
from time import monotonic


def encode_packet(packet):
    """Подготовить одну строку JSON для sendline."""
    return json.dumps(packet, ensure_ascii=False).encode("utf-8")


def read_packet(tube, timeout):
    """Прочитать пакет. При таймауте вернуть None, при обрыве — EOFError."""
    line = tube.recvuntil(b"\n", timeout=timeout)
    if not line:
        return None
    packet = json.loads(line.decode("utf-8"))
    if type(packet) is not dict or set(packet) != {
            "num", "type", "topic", "cmdid", "id", "data"}:
        raise ValueError("Нужны поля num, type, topic, cmdid, id и data.")
    if type(packet["num"]) is not int or packet["num"] < 1:
        raise ValueError("Номер пакета должен быть положительным целым.")
    if packet["type"] not in ("req", "resp"):
        raise ValueError("Тип пакета должен быть req или resp.")
    if packet["topic"] not in ("system", "lobby", "game", "chat"):
        raise ValueError("Неизвестный топик.")
    for field in ("cmdid", "id"):
        if type(packet[field]) is not str or not packet[field]:
            raise ValueError(f"Поле {field} должно быть непустой строкой.")
    if type(packet["data"]) is not dict:
        raise ValueError("Поле data должно содержать объект JSON.")
    return packet


class Protocol:
    """Номера, ожидаемые ACK и ответы на входящие запросы одного соединения."""

    def __init__(self, tube, timeout=1, attempts=3):
        """Задать ожидание ACK в секундах и число отправок, включая первую."""
        if timeout <= 0 or attempts < 1:
            raise ValueError("Нужны положительные timeout и attempts.")
        self.tube = tube
        self.timeout = timeout
        self.attempts = attempts
        self.next_num = 1
        self.pending = {}  # Свои запросы, для которых ещё нужен ответ.
        self.answers = {}  # Ответы на запросы другой стороны.

    def request(self, topic, cmdid, player_id, data):
        """Отправить req и вернуть его номер. При повторе номер сохранится."""
        num = self.next_num
        packet = dict(num=num, type="req", topic=topic, cmdid=cmdid,
                      id=player_id, data=data)
        line = encode_packet(packet)
        self.tube.sendline(line)
        self.next_num += 1
        self.pending[num] = dict(line=line, id=player_id, topic=topic,
                                 sent=1, deadline=monotonic() + self.timeout)
        return num

    def receive(self, handle_request):
        """Обслужить один пакет и повторы. Вызывать в цикле соединения.

        Для нового req обработчик возвращает пару (cmdid ответа, data).
        Для своего запроса метод один раз возвращает полученный resp.
        При ожидании или обработке чужого запроса возвращает None.
        После последней неудачной попытки закрывает соединение.
        """
        packet = read_packet(self.tube, self.timeout)
        response = None
        if packet is not None:
            num = packet["num"]
            if packet["type"] == "req":
                if num not in self.answers:
                    cmdid, data = handle_request(packet)
                    reply = dict(num=num, type="resp", topic=packet["topic"],
                                 cmdid=cmdid, id=packet["id"], data=data)
                    answer = encode_packet(reply)
                    self.answers[num] = (packet, answer)
                else:
                    original, answer = self.answers[num]
                    if original != packet:
                        raise ValueError(
                            "Этот номер уже занят другим запросом.")
                self.tube.sendline(answer)
            elif num in self.pending:
                item = self.pending[num]
                if (packet["id"] == item["id"]
                        and packet["topic"] == item["topic"]):
                    del self.pending[num]
                    response = packet

        for num, item in self.pending.items():
            if monotonic() >= item["deadline"]:
                if item["sent"] == self.attempts:
                    self.tube.close()
                    raise TimeoutError(f"Нет ACK на запрос №{num}. "
                                       f"Проверьте интернет.")
                self.tube.sendline(item["line"])
                item["sent"] += 1
                item["deadline"] = monotonic() + self.timeout
        return response

"""Обмен запросами и ответами по соединению pwntools.

Каждый пакет занимает одну строку JSON в UTF-8. Ответ (resp) подтверждает
получение запроса (req) и содержит те же num, topic и id. Команда ответа
может отличаться от команды запроса, например pong в ответ на ping.
"""

import json
from time import monotonic


from minotaur.exceptions import PacketError


def encode_packet(packet):
    """Закодировать пакет для отправки через sendline.

    Args:
        packet: Словарь с полями num, type, topic, cmdid, id и data.

    Returns:
        Байты JSON в UTF-8. Перевод строки добавляет sendline.

    Raises:
        TypeError: Пакет содержит значение, которое JSON не поддерживает.
        ValueError: Данные содержат циклическую ссылку.
    """
    return json.dumps(packet, ensure_ascii=False).encode("utf-8")


def read_packet(tube, timeout):
    """Прочитать одну строку JSON и проверить поля пакета.

    Args:
        tube: Открытое соединение pwntools.
        timeout: Время ожидания полной строки в секундах.

    Returns:
        Словарь с полями num (целое число от 1), type (req или resp),
        topic (system, lobby, game или chat), cmdid (команда), id (игрок)
        и data (словарь). Если строка не получена вовремя, возвращает None.

    Raises:
        PacketError: Ошибка декодирования UTF-8, синтаксиса JSON или полей
            пакета. Поля cmdid и id должны быть непустыми строками.
        EOFError: Соединение закрылось до получения полной строки.
    """
    line = tube.recvuntil(b"\n", timeout=timeout)
    if not line:
        return None
    try:
        packet = json.loads(line.decode("utf-8"))
    except UnicodeDecodeError:
        raise PacketError("Пакет должен быть в UTF-8.", "InvalidEncoding")
    except json.JSONDecodeError:
        raise PacketError("Не удалось прочитать JSON.", "InvalidJson")
    if type(packet) is dict and (
            type(packet.get("num")) is not int or packet["num"] < 1):
        raise PacketError("Нужен положительный целый num.", "InvalidNum")
    if type(packet) is not dict or set(packet) != {
            "num", "type", "topic", "cmdid", "id", "data"}:
        raise PacketError("Нужны поля num, type, topic, cmdid, id и data.",
                          "InvalidFields")
    if packet["type"] not in ("req", "resp"):
        raise PacketError("Тип пакета должен быть req или resp.",
                          "InvalidType")
    if packet["topic"] not in ("system", "lobby", "game", "chat"):
        raise PacketError("Неизвестный топик.", "UnknownTopic")
    for field in ("cmdid", "id"):
        if type(packet[field]) is not str or not packet[field]:
            raise PacketError(f"Поле {field} должно быть непустой строкой.",
                              "InvalidFields")
    if type(packet["data"]) is not dict:
        raise PacketError("Поле data должно содержать объект JSON.",
                          "InvalidData")
    return packet


class Protocol:
    """Отправлять запросы и обрабатывать ответы в одном соединении.

    Attributes:
        tube: Соединение pwntools для чтения и отправки пакетов.
        timeout: Время ожидания пакета и интервал до повтора в секундах.
        attempts: Максимальное число отправок запроса, включая первую.
        next_num: Номер следующего исходящего запроса. Отсчёт идёт с 1.
        pending: Исходящие запросы, ожидающие ответа. По номеру хранятся
            байты запроса, ID игрока, топик, число отправок и срок ожидания.
        answers: Словарь по номерам входящих запросов. Для каждого номера
            хранит исходный пакет и байты ответа на случай повтора.
    """

    def __init__(self, tube, timeout=1, attempts=3):
        """Настроить протокол для открытого соединения.

        Args:
            tube: Соединение pwntools.
            timeout: Время ожидания в секундах. По умолчанию 1 секунда.
            attempts: Число отправок с учётом первой. По умолчанию 3.

        Raises:
            ValueError: timeout не положителен или attempts меньше 1.
        """
        if timeout <= 0 or attempts < 1:
            raise ValueError("Нужны положительные timeout и attempts.")
        self.tube = tube
        self.timeout = timeout
        self.attempts = attempts
        self.next_num = 1
        self.pending = {}  # Свои запросы, для которых ещё нужен ответ.
        self.answers = {}  # Ответы на запросы другой стороны.

    def request(self, topic, cmdid, player_id, data):
        """Отправить запрос и сохранить его до получения ответа.

        Args:
            topic: Топик запроса (system, lobby, game или chat).
            cmdid: Название команды, например ping.
            player_id: Строковый ID игрока для поля id.
            data: Словарь с данными команды.

        Returns:
            Номер отправленного запроса. Ответ с этим номером можно
            получить при вызове receive.

        Raises:
            TypeError: Данные запроса содержат неподдерживаемый тип.
            ValueError: Данные запроса содержат циклическую ссылку.
            EOFError: Соединение закрылось при отправке запроса.
        """
        num = self.next_num
        packet = dict(num=num, type="req", topic=topic, cmdid=cmdid,
                      id=player_id, data=data)
        line = encode_packet(packet)
        self.tube.sendline(line)
        self.next_num += 1
        self.pending[num] = dict(line=line, id=player_id, topic=topic,
                                 sent=1, deadline=monotonic() + self.timeout)
        return num

    def receive(self, handle_request, player_id="unknown"):
        """Принять один пакет и повторить запросы, срок ожидания которых истёк.

        Вызывается в цикле соединения. На повтор входящего запроса
        отправляет сохранённый ответ без повторного вызова обработчика.
        На повреждённый пакет отправляет запрос system.error. При конфликте
        номеров возвращает отказ на запрос. next_num добавляется в данные
        только при ошибке нумерации и учитывает принятые входящие запросы.

        Args:
            handle_request: Функция для обработки нового входящего req.
                Принимает словарь пакета и возвращает пару (cmdid, data)
                с названием команды ответа и словарём данных.
            player_id: ID получателя system.error. До регистрации используется
                строка unknown, поскольку ID игрока ещё неизвестен.

        Returns:
            Словарь resp, если num, id и topic совпали с ожидаемым ответом.
            При таймауте чтения, обработке req или получении ответа без
            подходящего запроса возвращает None.

        Raises:
            ValueError: Ответ обработчика нельзя закодировать в JSON.
            TypeError: Ответ обработчика содержит неподдерживаемый тип.
            EOFError: Соединение закрылось при чтении или отправке.
            TimeoutError: Истёк срок ожидания ответа после последней
                отправки запроса. Метод закрывает соединение.
        """
        try:
            packet = read_packet(self.tube, self.timeout)
        except PacketError as error:
            data = dict(ok=False, error=str(error),
                        error_code=error.error_code)
            if error.error_code == "InvalidNum":
                data["next_num"] = max(self.answers, default=0) + 1
            self.request("system", "error", player_id, data)
            packet = None
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
                        data = dict(
                            ok=False,
                            error="Номер уже использован другим запросом.",
                            error_code="NumAlreadyUsed",
                            next_num=max(self.answers) + 1,
                        )
                        answer = encode_packet(dict(packet, type="resp",
                                                    data=data))
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

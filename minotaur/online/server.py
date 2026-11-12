"""Регистрация игроков и обработка системных команд сервера."""

import hashlib
from threading import Lock

from minotaur.constants import PLAYER_ID_LENGTH
from minotaur.online.protocol import Protocol


class Session:
    """Состояние одного клиентского соединения.

    Attributes:
        server: Сервер, который регистрирует игроков и хранит их сеансы.
        player_id: ID этого клиента после hello или None до регистрации.
        finished: Получена команда disconnect и соединение пора закрыть.
    """

    def __init__(self, server):
        """Создать сеанс для нового клиента.

        Args:
            server: Экземпляр GameServer для этого соединения.
        """
        self.server = server
        self.player_id = None
        self.finished = False

    def unregister(self):
        """Освободить ID этого соединения после выхода или обрыва связи."""
        self.server.unregister(self)

    def handle_request(self, packet):
        """Обработать команду и подготовить данные для ответа Protocol.

        Args:
            packet: Проверенный запрос клиента с полями протокола.

        Returns:
            Пара из исходного cmdid и словаря с результатом ok.
            При отказе поле error содержит причину.
        """
        cmd = packet["cmdid"]
        player_id = packet["id"]
        if packet["topic"] == "system" and cmd == "hello":
            nick = packet["data"].get("nick")
            if type(nick) is not str or not nick:
                return cmd, {"ok": False, "error": "Нужен ник игрока."}
            digest = hashlib.md5(nick.encode("utf-8")).hexdigest()
            if digest[:PLAYER_ID_LENGTH] != player_id:
                return cmd, {"ok": False, "error": "ID не соответствует нику."}
            if not self.server.register(self, player_id, nick):
                return cmd, {"ok": False, "error": "Игрок уже подключён."}
            return cmd, {"ok": True}

        if self.player_id is None:
            return cmd, {"ok": False, "error": "Сначала отправьте hello."}
        if player_id != self.player_id:
            return cmd, {"ok": False, "error": "ID принадлежит не вам."}
        if packet["topic"] == "system" and cmd == "disconnect":
            self.unregister()
            self.finished = True
            return cmd, {"ok": True}
        return cmd, {"ok": False, "error": "Неизвестная команда."}


class GameServer:
    """Принимать клиентские соединения с общим списком игроков.

    Attributes:
        players: Ники зарегистрированных игроков по ID.
        sessions: Активные сеансы по тем же ID.
        lock: Общая блокировка для регистрации и удаления из обоих словарей.
    """

    def __init__(self):
        """Начать работу с пустым списком игроков."""
        self.players = {}
        self.sessions = {}
        self.lock = Lock()

    def register(self, session, player_id, nick):
        """Зарегистрировать игрока и связать ID с его сеансом.

        Args:
            session: Сеанс, получивший hello.
            player_id: Проверенный ID игрока.
            nick: Ник игрока.

        Returns:
            True при регистрации, False, если сеанс или ID уже занят.
        """
        with self.lock:
            if session.player_id is not None or player_id in self.sessions:
                return False
            self.players[player_id] = nick
            self.sessions[player_id] = session
            session.player_id = player_id
            return True

    def unregister(self, session):
        """Удалить записи игрока и освободить ID его сеанса.

        Args:
            session: Сеанс, завершивший работу.
        """
        with self.lock:
            player_id = session.player_id
            if player_id is not None:
                del self.players[player_id]
                del self.sessions[player_id]
                session.player_id = None

    def serve_client(self, tube):
        """Обрабатывать запросы одного клиента до выхода или обрыва связи.

        Args:
            tube: Соединение, которое передаёт сервер pwntools.
        """
        session = Session(self)
        protocol = Protocol(tube)
        try:
            while not session.finished:
                protocol.receive(session.handle_request)
        except (EOFError, OSError, ValueError):
            pass
        finally:
            session.unregister()
            tube.close()

"""Регистрация игроков и управление лобби игрового сервера."""

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
        lobby_id: Номер текущего лобби или None.
        updates: Изменения состава лобби, ожидающие отправки этому клиенту.
    """

    def __init__(self, server):
        """Создать сеанс для нового клиента.

        Args:
            server: Экземпляр GameServer для этого соединения.
        """
        self.server = server
        self.player_id = None
        self.finished = False
        self.lobby_id = None
        self.updates = []

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
                return cmd, {"ok": False, "error": "Нужен ник игрока.",
                             "error_code": "InvalidNick"}
            digest = hashlib.md5(nick.encode("utf-8")).hexdigest()
            if digest[:PLAYER_ID_LENGTH] != player_id:
                return cmd, {"ok": False, "error": "ID не соответствует нику.",
                             "error_code": "InvalidPlayerId"}
            if not self.server.register(self, player_id, nick):
                return cmd, {"ok": False, "error": "Игрок уже подключён.",
                             "error_code": "PlayerAlreadyConnected"}
            return cmd, {"ok": True}

        if self.player_id is None:
            return cmd, {"ok": False, "error": "Сначала отправьте hello.",
                         "error_code": "HelloRequired"}
        if player_id != self.player_id:
            return cmd, {"ok": False, "error": "ID принадлежит не вам.",
                         "error_code": "WrongPlayerId"}
        if packet["topic"] == "lobby":
            return cmd, self.server.lobby_command(self, cmd, packet["data"])
        if packet["topic"] == "system" and cmd == "disconnect":
            self.unregister()
            self.finished = True
            return cmd, {"ok": True}
        return cmd, {"ok": False, "error": "Неизвестная команда.",
                     "error_code": "UnknownCommand"}


class GameServer:
    """Принимать клиентские соединения с общим списком игроков.

    Attributes:
        players: Ники зарегистрированных игроков по ID.
        sessions: Активные сеансы по тем же ID.
        lobbies: Лобби по номерам. Игроки перечислены в порядке входа.
        next_lobby_id: Номер следующего создаваемого лобби.
        lock: Блокировка общих данных игроков и лобби.
    """

    def __init__(self):
        """Начать работу с пустым списком игроков."""
        self.players = {}
        self.sessions = {}
        self.lobbies = {}
        self.next_lobby_id = 1
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
                if session.lobby_id is not None:
                    self._leave_lobby(session)
                del self.players[player_id]
                del self.sessions[player_id]
                session.player_id = None

    def _leave_lobby(self, session):
        """Убрать игрока из лобби под блокировкой вызывающего метода.

        Args:
            session: Сеанс участника лобби.
        """
        lobby = self.lobbies[session.lobby_id]
        del lobby["players"][session.player_id]
        if lobby["players"]:
            remaining = list(lobby["players"])[0]
            lobby["host_id"] = remaining
            self.sessions[remaining].updates.append(self._snapshot(lobby))
        else:
            del self.lobbies[session.lobby_id]
        session.lobby_id = None
        session.updates.clear()

    def _snapshot(self, lobby):
        """Скопировать состояние лобби для отправки после снятия блокировки.

        Args:
            lobby: Лобби под блокировкой сервера.

        Returns:
            Номер, имя, ID хозяина и копия словаря ников участников.
        """
        return dict(lobby, players=lobby["players"].copy())

    def lobby_command(self, session, cmd, data):
        """Выполнить команду лобби зарегистрированного клиента.

        Args:
            session: Сеанс отправителя.
            cmd: Команда list, create, join, leave или update.
            data: Данные команды. Для join нужен целый lobby_id.
                Для update достаточно пустого словаря. Команда запускает
                отправку текущего состояния всем участникам своего лобби.

        Returns:
            Данные ответа с полем ok и результатом или причиной отказа.
        """
        with self.lock:
            if cmd == "list":
                return {"ok": True, "lobbies": [
                    self._snapshot(lobby) for lobby in self.lobbies.values()
                ]}
            if cmd == "update":
                if session.lobby_id is None:
                    return {"ok": False, "error": "Вы не в лобби.",
                            "error_code": "NotInLobby"}
                lobby = self.lobbies[session.lobby_id]
                for member_id in lobby["players"]:
                    recipient = self.sessions[member_id]
                    recipient.updates.append(self._snapshot(lobby))
                return {"ok": True}
            if cmd == "leave":
                if session.lobby_id is None:
                    return {"ok": False, "error": "Вы не в лобби.",
                            "error_code": "NotInLobby"}
                self._leave_lobby(session)
                return {"ok": True}
            if cmd not in ("create", "join"):
                return {"ok": False, "error": "Неизвестная команда.",
                        "error_code": "UnknownCommand"}
            if session.lobby_id is not None:
                return {"ok": False, "error": "Вы уже в лобби.",
                        "error_code": "AlreadyInLobby"}
            player_id = session.player_id
            nick = self.players[player_id]
            if cmd == "create":
                lobby_id = self.next_lobby_id
                self.next_lobby_id += 1
                lobby = dict(lobby_id=lobby_id, name=nick, host_id=player_id,
                             players={player_id: nick})
                self.lobbies[lobby_id] = lobby
            else:
                lobby_id = data.get("lobby_id")
                if type(lobby_id) is not int or lobby_id not in self.lobbies:
                    return {"ok": False, "error": "Лобби не найдено.",
                            "error_code": "LobbyNotFound"}
                lobby = self.lobbies[lobby_id]
                if len(lobby["players"]) >= 2:
                    return {"ok": False, "error": "Лобби заполнено.",
                            "error_code": "LobbyFull"}
                lobby["players"][player_id] = nick
                for member_id in lobby["players"]:
                    if member_id != session.player_id:
                        recipient = self.sessions[member_id]
                        recipient.updates.append(self._snapshot(lobby))
            session.lobby_id = lobby_id
            return {"ok": True, "lobby": self._snapshot(lobby)}

    def serve_client(self, tube):
        """Обрабатывать запросы одного клиента до выхода или обрыва связи.

        Args:
            tube: Соединение, которое передаёт сервер pwntools.
        """
        session = Session(self)
        protocol = Protocol(tube)
        try:
            while not session.finished:
                with self.lock:
                    updates = session.updates
                    session.updates = []
                for lobby in updates:
                    protocol.request("lobby", "update", session.player_id,
                                     {"lobby": lobby})
                protocol.receive(session.handle_request,
                                 session.player_id or "unknown")
        except (EOFError, OSError):
            pass
        except Exception as error:
            print(error, flush=True)
        finally:
            session.unregister()
            tube.close()

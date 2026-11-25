"""Регистрация игроков, лобби и чат игрового сервера."""

import hashlib
from threading import Lock

from minotaur.constants import PLAYER_ID_LENGTH
from minotaur.exceptions import LevelError, MovementError
from minotaur.online.game import create_game, game_snapshot, play_turn
from minotaur.online.protocol import Protocol


class Session:
    """Состояние одного клиентского соединения.

    Attributes:
        server: Сервер, который регистрирует игроков и хранит их сеансы.
        player_id: ID этого клиента после hello или None до регистрации.
        finished: Получена команда disconnect и соединение пора закрыть.
        lobby_id: Номер текущего лобби или None.
        updates: Изменения состава лобби, ожидающие отправки этому клиенту.
        chat_updates: Команды чата и их данные, ожидающие отправки клиенту.
        start_updates: Команды подготовки партии для этого клиента.
        game_updates: Состояния игры, ожидающие отправки этому клиенту.
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
        self.chat_updates = []
        self.start_updates = []
        self.game_updates = []

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
        if packet["topic"] == "chat":
            return cmd, self.server.chat_command(self, cmd, packet["data"])
        if packet["topic"] == "game":
            return cmd, self.server.game_command(self, cmd, packet["data"])
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
        lobbies: Лобби по номерам с именем, seed, хозяином, никами участников
            и словарём ready по ID игроков. state хранит этап запуска:
            waiting, preparing, generating, loading, started или paused.
            start_id — номер попытки запуска, confirmed — ID подтвердивших
            текущий этап игроков, level — принятая карта или None.
            game и monsters хранят игровые объекты; next_player_id — очередь.
            game_update_id — номер обновления, game_waiting — кто должен
            подтвердить его получение перед следующим действием.
        histories: Списки сообщений чата по номерам лобби.
        next_lobby_id: Номер следующего создаваемого лобби.
        lock: Блокировка общих данных игроков и лобби.
    """

    def __init__(self):
        """Начать работу с пустым списком игроков."""
        self.players = {}
        self.sessions = {}
        self.lobbies = {}
        self.histories = {}
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

        При выходе из начатой партии сообщить оставшемуся игроку о паузе.

        Args:
            session: Сеанс участника лобби.
        """
        lobby = self.lobbies[session.lobby_id]
        was_started = lobby["state"] == "started"
        if lobby["state"] in ("preparing", "generating", "loading"):
            self._cancel_start(lobby, "Игрок отключился во время подготовки.")
        elif lobby["state"] == "started":
            lobby["state"] = "paused"
            lobby["game_waiting"] = []
            for player_id in lobby["players"]:
                self.sessions[player_id].game_updates.clear()
        del lobby["players"][session.player_id]
        del lobby["ready"][session.player_id]
        if lobby["players"]:
            remaining = list(lobby["players"])[0]
            lobby["host_id"] = remaining
            self.sessions[remaining].updates.append(self._snapshot(lobby))
            nick = self.players[session.player_id]
            self._chat_message(lobby, None, f"Игрок {nick} вышел из лобби.")
            if was_started:
                self._chat_message(
                    lobby, None, "Партия на паузе: ждём второго игрока.")
        else:
            del self.lobbies[session.lobby_id]
            del self.histories[session.lobby_id]
        session.lobby_id = None
        session.updates.clear()
        session.chat_updates.clear()
        session.start_updates.clear()
        session.game_updates.clear()

    def _cancel_start(self, lobby, message):
        """Отменить подготовку под блокировкой сервера.

        Args:
            lobby: Лобби, запуск которого отменяется.
            message: Причина отмены для чата.
        """
        lobby["state"] = "waiting"
        lobby["level"] = None
        lobby["confirmed"] = []
        lobby["game"] = None
        lobby["monsters"] = []
        lobby["next_player_id"] = None
        lobby["game_waiting"] = []
        for player_id in lobby["players"]:
            session = self.sessions[player_id]
            session.start_updates.clear()
            session.game_updates.clear()
            session.updates.append(self._snapshot(lobby))
        self._chat_message(lobby, None, message)

    def start_response(self, session, lobby_id, start_id, cmd, data):
        """Учесть ответ на серверный запрос подготовки или получения карты.

        Args:
            session: Ответивший клиент.
            lobby_id: Лобби исходного запроса.
            start_id: Номер попытки запуска в этом лобби.
            cmd: Команда исходного запроса prepare, generate или level.
            data: Данные ответа с булевым ok.
        """
        with self.lock:
            if session.lobby_id != lobby_id:
                return
            lobby = self.lobbies[lobby_id]
            expected = {"prepare": "preparing", "generate": "generating",
                        "level": "loading"}
            if (lobby["start_id"] != start_id
                    or lobby["state"] != expected[cmd]):
                return
            if data.get("ok") is not True:
                self._cancel_start(lobby, "Клиент отказался от подготовки.")
                return
            if cmd == "generate":
                return
            if session.player_id not in lobby["confirmed"]:
                lobby["confirmed"].append(session.player_id)
            if len(lobby["confirmed"]) != 2:
                return
            lobby["confirmed"] = []
            if cmd == "prepare":
                lobby["state"] = "generating"
                host = self.sessions[lobby["host_id"]]
                host.start_updates.append(("generate", {
                    "lobby_id": lobby_id, "start_id": start_id,
                    "seed": lobby["seed"], "players": lobby["players"].copy(),
                    "level_num": 0,
                }))
            else:
                lobby["state"] = "started"
                lobby["next_player_id"] = lobby["game"].rng.choice(
                    list(lobby["players"]))
                self._queue_game(lobby)
                self._chat_message(lobby, None, "Партия началась.")
            for player_id in lobby["players"]:
                self.sessions[player_id].updates.append(self._snapshot(lobby))

    def _chat_message(self, lobby, player_id, text):
        """Сохранить сообщение и поставить его в очередь всем участникам.

        Вызывается под блокировкой сервера.

        Args:
            lobby: Лобби получателей.
            player_id: ID автора или None для системного сообщения.
            text: Текст сообщения.

        Returns:
            Номер сообщения внутри истории этого лобби.
        """
        lobby_id = lobby["lobby_id"]
        history = self.histories[lobby_id]
        message = {
            "message_id": len(history) + 1,
            "from": player_id,
            "message": text,
        }
        history.append(message)
        data = {"lobby_id": lobby_id, "message": message}
        for member_id in lobby["players"]:
            self.sessions[member_id].chat_updates.append(("recv", data))
        return message["message_id"]

    def chat_command(self, session, cmd, data):
        """Отправить сообщение или получить историю своего лобби.

        Args:
            session: Зарегистрированный сеанс отправителя.
            cmd: send для отправки или history для чтения истории.
            data: Для send содержит непустую строку message.

        Returns:
            Данные ответа с ok. Для send возвращается message_id,
            для history возвращаются lobby_id и messages.
            При отказе возвращаются error и error_code.
        """
        with self.lock:
            if session.lobby_id is None:
                return {"ok": False, "error": "Вы не в лобби.",
                        "error_code": "NotInLobby"}
            lobby_id = session.lobby_id
            if cmd == "history":
                return {"ok": True, "lobby_id": lobby_id,
                        "messages": self.histories[lobby_id].copy()}
            if cmd != "send":
                return {"ok": False, "error": "Неизвестная команда.",
                        "error_code": "UnknownCommand"}
            message = data.get("message")
            if type(message) is not str or not message.strip():
                return {"ok": False, "error": "Нужен текст сообщения.",
                        "error_code": "InvalidMessage"}
            message_id = self._chat_message(
                self.lobbies[lobby_id], session.player_id, message)
            return {"ok": True, "message_id": message_id}

    def _queue_game(self, lobby):
        """Поставить состояние игры в очередь обоим под блокировкой сервера.

        Args:
            lobby: Лобби с созданными game и monsters.

        До подтверждения обоими следующий ход запрещён. Номер обновления
        позволяет отличить поздний ответ от ответа на текущее состояние.
        """
        lobby["game_update_id"] += 1
        lobby["game_waiting"] = list(lobby["players"])
        data = game_snapshot(lobby["game"], lobby["monsters"],
                             lobby["next_player_id"])
        data["lobby_id"] = lobby["lobby_id"]
        data["start_id"] = lobby["start_id"]
        data["update_id"] = lobby["game_update_id"]
        for player_id in lobby["players"]:
            self.sessions[player_id].game_updates.append(data)

    def game_command(self, session, cmd, data):
        """Выполнить move или skip от игрока, которому принадлежит очередь.

        Args:
            session: Зарегистрированный отправитель.
            cmd: move или skip.
            data: Для move содержит direction: up, down, left или right.
                Для skip достаточно пустого словаря.

        Returns:
            Словарь с ok. При отказе содержит error и error_code.
            Успех ставит game.update в очередь обоим участникам.
        """
        with self.lock:
            if session.lobby_id is None:
                return {"ok": False, "error": "Вы не в лобби.",
                        "error_code": "NotInLobby"}
            lobby = self.lobbies[session.lobby_id]
            if lobby["state"] != "started":
                return {"ok": False, "error": "Партия не идёт.",
                        "error_code": "GameNotStarted"}
            game = lobby["game"]
            if game.state != "Round":
                return {"ok": False, "error": "Уровень уже завершён.",
                        "error_code": "GameFinished"}
            if cmd not in ("move", "skip"):
                return {"ok": False, "error": "Неизвестная команда.",
                        "error_code": "UnknownCommand"}
            if lobby["game_waiting"]:
                return {"ok": False, "error": "Ждём подтверждения состояния.",
                        "error_code": "UpdatePending"}
            if not game.level.players[session.player_id].is_alive:
                return {"ok": False, "error": "Игрок погиб.",
                        "error_code": "PlayerDead"}
            if session.player_id != lobby["next_player_id"]:
                return {"ok": False, "error": "Сейчас ход другого игрока.",
                        "error_code": "NotYourTurn"}
            action = " "
            if cmd == "move":
                keys = {"up": "w", "down": "s", "left": "a", "right": "d"}
                direction = data.get("direction")
                if type(direction) is not str or direction not in keys:
                    return {"ok": False, "error": "Неизвестное направление.",
                            "error_code": "InvalidMove"}
                action = keys[direction]
            try:
                play_turn(game, lobby["monsters"], session.player_id, action)
            except MovementError as error:
                return {"ok": False, "error": str(error),
                        "error_code": "InvalidMove"}
            next_player = None
            if game.state == "Round":
                next_player = session.player_id
                for player_id, player in game.level.players.items():
                    if (player.is_alive and player_id not in game.escaped
                            and player_id != session.player_id):
                        next_player = player_id
            lobby["next_player_id"] = next_player
            self._queue_game(lobby)
            return {"ok": True}

    def game_response(self, session, lobby_id, start_id, update_id, data):
        """Учесть подтверждение game.update только для текущего обновления.

        Args:
            session: Ответивший клиент.
            lobby_id: Номер лобби исходного запроса.
            start_id: Попытка запуска исходного запроса.
            update_id: Номер отправленного состояния игры.
            data: Ответ с ok=True при успешном получении состояния.

        Отказ приостанавливает партию. После двух ACK поражения карта
        удаляется, готовность сбрасывается, игроки остаются в своём лобби.
        """
        with self.lock:
            if session.lobby_id != lobby_id:
                return
            lobby = self.lobbies[lobby_id]
            if (lobby["state"] != "started"
                    or lobby["start_id"] != start_id
                    or lobby["game_update_id"] != update_id
                    or session.player_id not in lobby["game_waiting"]):
                return
            if data.get("ok") is not True:
                lobby["state"] = "paused"
                lobby["game_waiting"] = []
                for player_id in lobby["players"]:
                    member = self.sessions[player_id]
                    member.game_updates.clear()
                    member.updates.append(self._snapshot(lobby))
                self._chat_message(lobby, None,
                                   "Пауза: игрок не принял состояние игры.")
                return
            lobby["game_waiting"].remove(session.player_id)
            if not lobby["game_waiting"] and lobby["game"].state == "Lose":
                lobby["state"] = "waiting"
                lobby["level"] = None
                lobby["game"] = None
                lobby["monsters"] = []
                lobby["next_player_id"] = None
                for player_id in lobby["players"]:
                    lobby["ready"][player_id] = False
                for player_id in lobby["players"]:
                    self.sessions[player_id].updates.append(
                        self._snapshot(lobby))
                self._chat_message(lobby, None,
                                   "Поражение. Можно начать новую партию.")

    def _snapshot(self, lobby):
        """Скопировать состояние лобби для отправки после снятия блокировки.

        Args:
            lobby: Лобби под блокировкой сервера.

        Returns:
            Номер, имя, seed, ID хозяина, state, start_id и копии players
            и ready. can_start равен True до запуска, если двое готовы.
            Карта и внутренний список подтверждений в ответ не попадают.
        """
        result = dict(lobby_id=lobby["lobby_id"], name=lobby["name"],
                      seed=lobby["seed"], host_id=lobby["host_id"],
                      state=lobby["state"], start_id=lobby["start_id"])
        result["players"] = lobby["players"].copy()
        result["ready"] = lobby["ready"].copy()
        result["can_start"] = (
            lobby["state"] == "waiting" and len(lobby["players"]) == 2
            and all(lobby["ready"].values())
        )
        return result

    def lobby_command(self, session, cmd, data):
        """Выполнить команду лобби зарегистрированного клиента.

        Args:
            session: Сеанс отправителя.
            cmd: list, create, join, leave, update, configure,
                ready, unready, start или level.
            data: Данные команды. Для join нужен целый lobby_id.
                Для update достаточно пустого словаря. Команда запускает
                отправку текущего состояния всем участникам своего лобби.
                configure принимает name (непустая строка) и/или seed
                (целое число либо None для случайной генерации).
                ready, unready и start принимают пустой словарь.
                level принимает start_id и словарь level от хозяина.
                Вместо level можно передать ok=False при ошибке генерации.

        Returns:
            Данные ответа с полем ok и результатом или причиной отказа.
        """
        with self.lock:
            if cmd == "list":
                return {"ok": True, "lobbies": [
                    self._snapshot(lobby) for lobby in self.lobbies.values()
                ]}
            if cmd in ("start", "level"):
                if session.lobby_id is None:
                    return {"ok": False, "error": "Вы не в лобби.",
                            "error_code": "NotInLobby"}
                lobby = self.lobbies[session.lobby_id]
                if session.player_id != lobby["host_id"]:
                    return {"ok": False, "error": "Нужны права хозяина.",
                            "error_code": "HostRequired"}
                if cmd == "start":
                    if not self._snapshot(lobby)["can_start"]:
                        return {"ok": False, "error": "Нужны двое готовых.",
                                "error_code": "CannotStart"}
                    lobby["state"] = "preparing"
                    lobby["start_id"] += 1
                    lobby["confirmed"] = []
                    for player_id in lobby["players"]:
                        member = self.sessions[player_id]
                        member.start_updates.append(("prepare", {
                            "lobby_id": session.lobby_id,
                            "start_id": lobby["start_id"],
                        }))
                        member.updates.append(self._snapshot(lobby))
                    return {"ok": True, "start_id": lobby["start_id"]}
                if (lobby["state"] != "generating"
                        or type(data.get("start_id")) is not int
                        or data["start_id"] != lobby["start_id"]):
                    return {"ok": False, "error": "Эта карта сейчас не нужна.",
                            "error_code": "UnexpectedLevel"}
                if data.get("ok") is False:
                    self._cancel_start(lobby, "Хозяин не смог создать карту.")
                    return {"ok": True}
                level = data.get("level")
                try:
                    if type(level) is not dict:
                        raise LevelError("Нужны данные карты.")
                    if type(level.get("players")) is not dict:
                        raise LevelError("Нужен словарь игроков карты.")
                    if set(level["players"]) != set(lobby["players"]):
                        raise LevelError("Игроки карты не совпадают с лобби.")
                    game, monsters = create_game(
                        level, lobby["players"], lobby["seed"])
                except (LevelError, KeyError, TypeError, ValueError) as error:
                    self._cancel_start(lobby, "Получена некорректная карта.")
                    return {"ok": False, "error": str(error),
                            "error_code": "InvalidLevel"}
                lobby["level"] = level
                lobby["game"] = game
                lobby["monsters"] = monsters
                lobby["state"] = "loading"
                lobby["confirmed"] = []
                for player_id in lobby["players"]:
                    member = self.sessions[player_id]
                    member.start_updates.append(("level", {
                        "lobby_id": session.lobby_id,
                        "start_id": lobby["start_id"], "level": level,
                    }))
                    member.updates.append(self._snapshot(lobby))
                return {"ok": True}
            if cmd in ("update", "configure", "ready", "unready"):
                if session.lobby_id is None:
                    return {"ok": False, "error": "Вы не в лобби.",
                            "error_code": "NotInLobby"}
                lobby = self.lobbies[session.lobby_id]
                if cmd != "update" and lobby["state"] != "waiting":
                    return {"ok": False, "error": "Подготовка уже началась.",
                            "error_code": "LobbyLocked"}
                message = None
                nick = self.players[session.player_id]
                if cmd == "configure":
                    if session.player_id != lobby["host_id"]:
                        return {"ok": False, "error": "Нужны права хозяина.",
                                "error_code": "HostRequired"}
                    if not data or set(data) - {"name", "seed"}:
                        return {"ok": False, "error": "Нужны name и/или seed.",
                                "error_code": "InvalidSettings"}
                    name = data.get("name", lobby["name"])
                    seed = data.get("seed", lobby["seed"])
                    if type(name) is not str or not name.strip():
                        return {"ok": False, "error": "Нужно имя лобби.",
                                "error_code": "InvalidLobbyName"}
                    if seed is not None and type(seed) is not int:
                        return {"ok": False, "error": "Нужен целый seed.",
                                "error_code": "InvalidSeed"}
                    if name != lobby["name"] or seed != lobby["seed"]:
                        lobby["name"] = name
                        lobby["seed"] = seed
                        message = f"{nick} изменил настройки лобби."
                if cmd in ("ready", "unready"):
                    ready = cmd == "ready"
                    if lobby["ready"][session.player_id] != ready:
                        lobby["ready"][session.player_id] = ready
                        if ready:
                            message = f"Игрок {nick} готов."
                        else:
                            message = f"Игрок {nick} отменил готовность."
                for member_id in lobby["players"]:
                    recipient = self.sessions[member_id]
                    recipient.updates.append(self._snapshot(lobby))
                if message is not None:
                    self._chat_message(lobby, None, message)
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
                             players={player_id: nick}, seed=None,
                             ready={player_id: False}, state="waiting",
                             start_id=0, confirmed=[], level=None,
                             game=None, monsters=[], next_player_id=None,
                             game_update_id=0, game_waiting=[])
                self.lobbies[lobby_id] = lobby
                self.histories[lobby_id] = []
            else:
                lobby_id = data.get("lobby_id")
                if type(lobby_id) is not int or lobby_id not in self.lobbies:
                    return {"ok": False, "error": "Лобби не найдено.",
                            "error_code": "LobbyNotFound"}
                lobby = self.lobbies[lobby_id]
                if lobby["state"] not in ("waiting", "paused"):
                    return {"ok": False, "error": "Лобби уже запускается.",
                            "error_code": "LobbyLocked"}
                if len(lobby["players"]) >= 2:
                    return {"ok": False, "error": "Лобби заполнено.",
                            "error_code": "LobbyFull"}
                lobby["players"][player_id] = nick
                lobby["ready"][player_id] = False
                session.chat_updates.append(("history", {
                    "lobby_id": lobby_id,
                    "messages": self.histories[lobby_id].copy(),
                }))
                self._chat_message(lobby, None,
                                   f"Игрок {nick} вошёл в лобби.")
                for member_id in lobby["players"]:
                    if member_id != session.player_id:
                        recipient = self.sessions[member_id]
                        recipient.updates.append(self._snapshot(lobby))
            session.lobby_id = lobby_id
            return {"ok": True, "lobby": self._snapshot(lobby)}

    def serve_client(self, tube):
        """Обрабатывать запросы одного клиента до выхода или обрыва связи.

        Ответы на prepare и level подтверждают этап запуска. generate
        подтверждается сразу; готовую карту хозяин присылает отдельным
        запросом level. start_requests связывает num с попыткой запуска;
        запросы отменённых попыток удаляются из ожидания Protocol.
        game_requests аналогично связывает ACK с номером game.update.

        Args:
            tube: Соединение, которое передаёт сервер pwntools.
        """
        session = Session(self)
        protocol = Protocol(tube)
        start_requests = {}
        game_requests = {}
        try:
            while not session.finished:
                with self.lock:
                    updates = session.updates
                    session.updates = []
                    chat_updates = session.chat_updates
                    session.chat_updates = []
                    start_updates = session.start_updates
                    session.start_updates = []
                    game_updates = session.game_updates
                    session.game_updates = []
                    for num, (lobby_id, start_id, update_id) in list(
                            game_requests.items()):
                        lobby = self.lobbies.get(lobby_id)
                        if (lobby is None or session.lobby_id != lobby_id
                                or lobby["start_id"] != start_id
                                or lobby["game_update_id"] != update_id
                                or lobby["state"] != "started"):
                            protocol.pending.pop(num, None)
                            del game_requests[num]
                    for num, (lobby_id, start_id, cmd) in list(
                            start_requests.items()):
                        lobby = self.lobbies.get(lobby_id)
                        if (session.lobby_id != lobby_id or lobby is None
                                or lobby["start_id"] != start_id
                                or lobby["state"] in
                                ("waiting", "paused", "started")
                                or (cmd == "generate"
                                    and lobby["state"] == "loading")):
                            protocol.pending.pop(num, None)
                            del start_requests[num]
                for lobby in updates:
                    protocol.request("lobby", "update", session.player_id,
                                     {"lobby": lobby})
                for cmd, data in chat_updates:
                    protocol.request("chat", cmd, session.player_id, data)
                for cmd, data in start_updates:
                    num = protocol.request(
                        "lobby", cmd, session.player_id, data)
                    start_requests[num] = (data["lobby_id"],
                                           data["start_id"], cmd)
                for data in game_updates:
                    num = protocol.request(
                        "game", "update", session.player_id, data)
                    game_requests[num] = (data["lobby_id"], data["start_id"],
                                          data["update_id"])
                response = protocol.receive(session.handle_request,
                                            session.player_id or "unknown")
                if response is not None and response["num"] in start_requests:
                    request = start_requests.pop(response["num"])
                    lobby_id, start_id, cmd = request
                    self.start_response(session, lobby_id, start_id, cmd,
                                        response["data"])
                if response is not None and response["num"] in game_requests:
                    lobby_id, start_id, update_id = game_requests.pop(
                        response["num"])
                    self.game_response(session, lobby_id, start_id, update_id,
                                       response["data"])
        except (EOFError, OSError):
            pass
        except Exception as error:
            print(error, flush=True)
        finally:
            session.unregister()
            tube.close()

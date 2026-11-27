"""Запуск игрового сервера из корня проекта."""

import argparse
from time import sleep

from pwnlib.tubes.server import server

from minotaur.online.server import GameServer


def main():
    """Слушать TCP-порт из аргумента --port до нажатия Ctrl+C."""
    parser = argparse.ArgumentParser(description="Сервер Минотавра")
    parser.add_argument("--port", type=int, default=1234)
    args = parser.parse_args()
    game = GameServer()
    listener = server(args.port, fam="ipv4", callback=game.serve_client)
    print(f"Сервер слушает порт {listener.lport}", flush=True)
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        listener.close()


if __name__ == "__main__":
    main()

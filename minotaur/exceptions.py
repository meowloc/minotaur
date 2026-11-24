"""Исключения проекта."""


# Ошибки генерации и размещения объектов

class MinotaurError(Exception):
    """Базовый класс всех ошибок в игре."""


class LevelError(MinotaurError, ValueError):
    """Ошибка при некорректном лабиринте, клетке или иных объектах уровня."""


class GenerationError(MinotaurError, ValueError):
    """Ошибка входных данных при генерации лабиринта."""


class PacketError(MinotaurError, ValueError):
    """Ошибка входящего пакета.

    Attributes:
        error_code: Короткое имя ошибки для обработки клиентом.
    """

    def __init__(self, message, error_code):
        """Сохранить описание и код ошибки.

        Args:
            message: Понятное описание проблемы.
            error_code: Имя ошибки, например InvalidJson.
        """
        super().__init__(message)
        self.error_code = error_code


class PlaceError(MinotaurError, ValueError):
    """Ошибка при размещении объектов на карте."""

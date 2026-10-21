"""Исключения проекта."""


# Ошибки генерации и размещения объектов

class MinotaurError(Exception):
    """Базовый класс всех ошибок в игре."""


class LevelError(MinotaurError, ValueError):
    """Ошибка при некорректном лабиринте, клетке или иных объектах уровня."""


class GenerationError(MinotaurError, ValueError):
    """Ошибка входных данных при генерации лабиринта."""


class PlaceError(MinotaurError, ValueError):
    """Ошибка при размещении объектов на карте."""

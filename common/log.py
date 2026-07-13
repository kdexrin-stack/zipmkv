from __future__ import annotations

from collections.abc import Callable


Logger = Callable[[str], None]


def emit(log: Logger | None, message: str) -> None:
    if log:
        log(message)

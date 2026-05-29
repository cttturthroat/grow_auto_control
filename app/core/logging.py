from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from loguru import logger

from app.core.config import settings

if TYPE_CHECKING:
    from loguru import Logger, Message


def _is_frozen() -> bool:
    # sys._MEIPASS is set by PyInstaller before any user code runs; it is the
    # most reliable signal that we are running inside a packaged executable.
    return hasattr(sys, '_MEIPASS') or bool(getattr(sys, 'frozen', False))


def _exe_dir() -> Path:
    """Return the directory that contains grow_control.exe (or the project root in dev)."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def setup_logging() -> None:
    logger.remove()

    logger.add(
        sys.stderr,
        format=(
            '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | '
            '<level>{level: <8}</level> | '
            '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
            '<level>{message}</level>'
        ),
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    if _is_frozen():
        log_path = _exe_dir() / 'grow_control.log'
        logger.add(
            str(log_path),
            format=(
                '{time:YYYY-MM-DD HH:mm:ss} | '
                '{level: <8} | '
                '{name}:{function}:{line} - '
                '{message}'
            ),
            level=settings.LOG_LEVEL,
            rotation='1 MB',
            retention=3,
            encoding='utf-8',
            backtrace=True,
            diagnose=True,
            delay=False,
        )


def add_gui_sink(callback: Callable[[str], None]) -> int:
    def _sink(message: Message) -> None:
        callback(str(message))

    return logger.add(  # type: ignore[call-overload]
        _sink,
        format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
        level=settings.LOG_LEVEL,
        colorize=False,
    )


def remove_gui_sink(sink_id: int) -> None:
    logger.remove(sink_id)


def get_logger(name: str | None = None) -> Logger:
    if name:
        return logger.bind(name=name)
    return logger

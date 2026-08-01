"""Logging terpusat dan penanganan error global."""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from config import LOGS_DIR

LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "manager.log"

log = logging.getLogger("ibeks_manager")
log.setLevel(logging.INFO)
if not log.handlers:
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [IBEKS MANAGER BOT] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    log.addHandler(file_handler)
    log.addHandler(stream_handler)


def log_exception(context: str, exc: BaseException) -> None:
    """Catat exception dengan konteks yang jelas."""
    log.exception("%s: %s", context, exc)


def install_global_error_handler() -> None:
    """Pasang handler untuk exception utama, thread, dan event loop."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if exc_value is not None:
            log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

    def handle_thread_exception(args):
        log.critical(
            "Unhandled thread exception in %s",
            args.thread.name if args.thread else "unknown",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception

    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(
            lambda _loop, context: log.error(
                "Unhandled asyncio exception: %s",
                context.get("exception") or context.get("message"),
                exc_info=context.get("exception"),
            )
        )
    except RuntimeError:
        # Event loop akan dibuat oleh Pyrogram saat client dijalankan.
        pass


def safe_handler(func: Callable[..., Awaitable[Any]]):
    """Tangkap exception handler agar satu update tidak menghentikan bot."""
    @wraps(func)
    async def wrapped(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            log_exception(f"Handler {func.__name__} gagal", exc)
            return None

    return wrapped

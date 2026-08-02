"""Logging file/console dan wrapper error global Manager Bot."""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from config import LOGS_DIR

LOGS_DIR.mkdir(parents=True, exist_ok=True)
log = logging.getLogger("ibeks.manager")
log.setLevel(logging.INFO)
log.propagate = False

if not log.handlers:
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(LOGS_DIR / "manager.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    log.addHandler(file_handler)
    log.addHandler(stream_handler)


def install_global_error_handler() -> None:
    """Catat exception asyncio tanpa menghentikan event loop."""
    loop = asyncio.get_event_loop()

    def handler(loop, context):
        error = context.get("exception")
        if error:
            log.error(
                "Global asyncio error: %s",
                context.get("message"),
                exc_info=error,
            )
        else:
            log.error("Global asyncio error: %s", context.get("message"))

    loop.set_exception_handler(handler)


def safe_handler(function: Callable[..., Awaitable[Any]]):
    """Pastikan error satu handler tidak membuat bot crash."""

    @wraps(function)
    async def wrapped(client, update, *args, **kwargs):
        try:
            return await function(client, update, *args, **kwargs)
        except Exception:
            log.exception("Handler %s gagal.", function.__name__)
            try:
                if hasattr(update, "answer"):
                    await update.answer(
                        "Terjadi kesalahan. Silakan coba lagi.",
                        show_alert=True,
                    )
                elif hasattr(update, "reply"):
                    await update.reply("❌ Terjadi kesalahan. Silakan coba lagi.")
            except Exception:
                log.exception(
                    "Gagal mengirim pesan error dari handler %s.",
                    function.__name__,
                )

    return wrapped
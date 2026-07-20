"""
IBEKS USERBOT - Global Error Handler
Menangkap error dari handler plugin, mencatatnya ke log file,
dan mencegah bot crash akibat error plugin.
"""

import asyncio
import functools
import traceback
from typing import Callable

from pyrogram import Client
from pyrogram.types import Message

from utils.logger import log


HandlerType = Callable[[Client, Message], object]


def _handle_task_error(task) -> None:
    """Callback untuk menangkap error dari async task handler."""
    try:
        task.result()
    except Exception as exc:
        name = getattr(task, "__handler_name__", "unknown")
        tb = traceback.format_exc()
        log.exception(f"[ErrorHandler] Error di handler '{name}': {exc}\n{tb}")


def wrap_handler(handler: HandlerType) -> HandlerType:
    """
    Bungkus handler Pyrogram agar error ditangkap dan dicatat.
    Error tidak akan diteruskan ke atas sehingga bot tetap berjalan.

    Wrapper ini bersifat synchronous sehingga kompatibel dengan mekanisme
    dispatcher Pyrogram 2.x, dan menjalankan handler async di dalam task.
    """
    @functools.wraps(handler)
    def wrapper(client: Client, message: Message):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            log.error(f"[ErrorHandler] Tidak ada event loop saat menjalankan {handler.__name__}")
            return

        task = loop.create_task(handler(client, message))
        task.__handler_name__ = getattr(handler, "__name__", "unknown")
        task.add_done_callback(_handle_task_error)

    return wrapper


def patch_client_handlers(client: Client) -> None:
    """
    Patch `client.on_message` sehingga setiap handler yang didaftarkan
    secara otomatis dibungkus dengan error handler.
    Panggil fungsi ini sebelum load_plugins().
    """
    original_on_message = client.on_message

    def wrapped_on_message(filters=None, group: int = 0):
        # Jika on_message dipanggil sebagai decorator tanpa argumen, filters adalah handler
        if callable(filters) and not hasattr(filters, "filters"):
            handler = filters
            wrapped = wrap_handler(handler)
            return original_on_message(wrapped, group)

        def decorator(handler):
            wrapped = wrap_handler(handler)
            return original_on_message(filters, group)(wrapped)
        return decorator

    client.on_message = wrapped_on_message

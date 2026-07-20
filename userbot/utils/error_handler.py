"""
IBEKS USERBOT - Global Error Handler
Menangkap error dari handler plugin, mencatatnya ke log file,
dan mencegah bot crash akibat error plugin.
"""

import functools
import traceback
from typing import Callable

from pyrogram import Client
from pyrogram.types import Message

from utils.logger import log


HandlerType = Callable[[Client, Message], object]


def wrap_handler(handler: HandlerType) -> HandlerType:
    """
    Bungkus handler Pyrogram agar error ditangkap dan dicatat.
    Error tidak akan diteruskan ke atas sehingga bot tetap berjalan.
    """
    @functools.wraps(handler)
    async def wrapper(client: Client, message: Message):
        try:
            return await handler(client, message)
        except Exception as exc:
            name = getattr(handler, "__name__", "unknown")
            tb = traceback.format_exc()
            log.exception(f"[ErrorHandler] Error di handler '{name}': {exc}\n{tb}")
            # Diam-diam tolak error agar Pyrogram tidak menyerahkannya
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

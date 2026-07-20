"""
IBEKS USERBOT - Global Error Handler
Menangkap error tak terduga secara global, mencatatnya ke log file,
dan mencegah bot crash akibat error plugin.

Pyrogram sendiri sudah menangkap error di handler plugin sehingga bot
 tidak crash. Error handler di sini menangkap error di luar handler
(uncaught exception) dan memastikan log tetap tersimpan di file.
"""

import asyncio
import sys
import traceback

from utils.logger import log


def _handle_exception(exc_type, exc_value, exc_traceback) -> None:
    """Hook sys.excepthook untuk menangkap exception tak tertangani."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log.exception(f"[GlobalError] Uncaught exception: {exc_value}\n{tb}")


def _handle_async_exception(loop, context) -> None:
    """Hook asyncio exception handler untuk menangkap error di event loop."""
    message = context.get("message", "Unknown async error")
    exception = context.get("exception")
    if exception:
        tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
        log.exception(f"[GlobalError] Async error: {message}\n{''.join(tb)}")
    else:
        log.error(f"[GlobalError] Async error: {message}")


def install_global_error_handler() -> None:
    """Pasang hook global untuk menangkap error dan mencatatnya ke log."""
    sys.excepthook = _handle_exception

    try:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(_handle_async_exception)
    except RuntimeError:
        # Belum ada loop yang running; biarkan Pyrogram mengatur loop-nya nanti
        pass

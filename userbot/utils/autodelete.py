"""
IBEKS USERBOT - Auto Delete Utility
Menghapus pesan secara otomatis setelah jeda tertentu.
Dapat digunakan oleh semua plugin dengan memanggil auto_delete().
"""

import asyncio

from utils.logger import log


async def auto_delete(message, delay: int = 5) -> None:
    """
    Hapus `message` setelah `delay` detik.

    Parameters
    ----------
    message : pyrogram.types.Message
        Pesan yang akan dihapus.
    delay : int
        Jeda dalam detik sebelum pesan dihapus (default: 5).
    """
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as exc:
        log.warning(f"[AutoDelete] Gagal menghapus pesan {message.id}: {exc}")

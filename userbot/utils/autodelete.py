"""
IBEKS USERBOT - Auto Delete Utility
Menghapus pesan command tertentu secara otomatis setelah jeda tertentu.

Semua plugin boleh tetap memanggil auto_delete(), tetapi hanya command yang
terdaftar di AUTO_DELETE_COMMANDS yang akan dihapus. Dengan begitu, perilaku
default seluruh command tetap mempertahankan riwayat chat dan daftar command
yang memakai auto-delete dapat diubah dari satu tempat.
"""

import asyncio
from typing import Any

from utils.logger import log
from utils.prefix_manager import get_prefix


# Command tanpa prefix yang pesan command-nya boleh dihapus otomatis.
# Tambahkan/hapus nama command di sini; plugin tidak perlu diubah.
AUTO_DELETE_COMMANDS = {"clone", "joinvc", "restore"}


def should_auto_delete(message: Any) -> bool:
    """Kembalikan True hanya untuk pesan command di allowlist."""
    if not message or (not message.text and not message.caption):
        return False

    text = (message.text or message.caption).strip()
    if not text:
        return False

    command = text.split(maxsplit=1)[0]
    prefix = get_prefix()
    return any(command == f"{prefix}{name}" for name in AUTO_DELETE_COMMANDS)


async def auto_delete(message, delay: int = 5, force: bool = False) -> None:
    """
    Hapus pesan command yang diizinkan setelah `delay` detik.

    Pesan non-command atau command yang tidak ada di allowlist diabaikan.

    Parameters
    ----------
    message : pyrogram.types.Message
        Pesan yang akan dihapus.
    delay : int
        Jeda dalam detik sebelum pesan dihapus (default: 5).
    """
    if not force and not should_auto_delete(message):
        return

    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as exc:
        log.warning(f"[AutoDelete] Gagal menghapus pesan {message.id}: {exc}")

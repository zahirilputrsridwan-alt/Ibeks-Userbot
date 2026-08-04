"""
IBEKS USERBOT - Fun Tahap 9
Command:
  .ckocok - animasi kocok dan hasil lucu

Hasil akhir dibuat stabil berdasarkan User ID + minggu ISO berjalan,
sehingga tidak berubah-ubah setiap command dan tidak membutuhkan database.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command


_ANIMATION_FRAMES = (
    "8✊==D",
    "8=✊=D",
    "8==✊=D",
    "8=✊===D",
    "8==✊==D",
    "8====✊D💦👄",
)

_RESULTS = (
    "💦 Ahhhh 😩",
    "💦 Lagi semangat 😭",
    "💦 Cape juga...",
)


def _week_key() -> str:
    """Kunci minggu UTC untuk hasil yang stabil selama minggu berjalan."""
    iso = datetime.now(timezone.utc).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _result_for_user(user_id: int) -> str:
    """Pilih hasil berbeda per user tanpa random global atau penyimpanan state."""
    digest = hashlib.sha256(f"ckocok:{user_id}:{_week_key()}".encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "big") % len(_RESULTS)
    return _RESULTS[index]


async def _animate(message) -> None:
    """Tampilkan animasi secara berurutan pada pesan hasil yang sama."""
    # Frame pertama sudah dikirim oleh caller. Mengedit ke teks identik akan
    # memicu MessageNotModified dari Telegram dan menghentikan animasi.
    for frame in _ANIMATION_FRAMES[1:]:
        await asyncio.sleep(1.0)
        await message.edit_text(frame)


def setup(client):
    """Daftarkan hanya command .ckocok."""

    @client.on_message(dynamic_command("ckocok") & filters.me)
    async def cmd_ckocok(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        result_message = await client.send_message(message.chat.id, _ANIMATION_FRAMES[0])
        try:
            await _animate(result_message)
            result = _result_for_user(message.from_user.id)
            await result_message.edit_text(result)
        except Exception as exc:
            # Animasi tidak boleh membuat hasil akhir hilang jika Telegram
            # menolak salah satu edit (misalnya pesan dihapus lebih dulu).
            logging.exception("[Stage9] Animasi .ckocok gagal: %s", exc)
            try:
                result = _result_for_user(message.from_user.id)
                await result_message.edit_text(result)
            except Exception as result_exc:
                logging.exception("[Stage9] Gagal mengirim hasil .ckocok: %s", result_exc)
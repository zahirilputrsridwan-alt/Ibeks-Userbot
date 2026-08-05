"""IBEKS USERBOT - Plugin Restore.

Command:
  .restore - pulihkan profil terakhir yang dibackup oleh .clone
"""

import asyncio
import json
import os

from pyrogram import filters
from pyrogram.errors import RPCError

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.logger import log
from plugins.fun.clone import BACKUP_METADATA_PATH, BACKUP_PHOTO_PATH
from plugins.utils.ui import send_ui


def _telegram_error(exc: Exception) -> str:
    reason = str(exc).strip()
    return reason or exc.__class__.__name__


async def _notify(client, chat_id: int, text: str) -> None:
    try:
        await send_ui(
            client,
            chat_id,
            "╭─「 ♻️ 𝗥𝗘𝗦𝗧𝗢𝗥𝗘 」\n│\n"
            f"├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ {text}\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
        )
    except Exception as exc:
        log.exception("[Restore] Gagal mengirim status ke chat %s: %s", chat_id, exc)


def _load_backup() -> dict | None:
    if not os.path.exists(BACKUP_METADATA_PATH):
        return None
    try:
        with open(BACKUP_METADATA_PATH, "r", encoding="utf-8") as file:
            backup = json.load(file)
        if not isinstance(backup, dict):
            raise ValueError("format backup tidak valid")
        required = ("first_name", "last_name", "bio")
        if any(key not in backup for key in required):
            raise ValueError("data backup tidak lengkap")
        return backup
    except Exception as exc:
        log.exception("[Restore] Gagal membaca backup: %s", exc)
        return None


async def _remove_current_photo(client) -> None:
    """Hapus foto profil saat backup awal memang tidak memiliki foto."""
    me = await client.get_me()
    if not me.photo:
        return
    photo_id = getattr(me.photo, "file_id", None) or me.photo.big_file_id
    await client.delete_profile_photos(photo_id)


async def restore_profile(client) -> tuple[bool, str]:
    """Jalankan restore profil dan kembalikan status untuk pemanggil UI."""
    backup = _load_backup()
    if backup is None:
        return False, "Backup profil tidak ditemukan."

    errors = []
    try:
        await client.update_profile(
            first_name=backup["first_name"],
            last_name=backup["last_name"],
            bio=backup["bio"],
        )
    except RPCError as exc:
        errors.append(f"data profil ({_telegram_error(exc)})")
        log.exception("[Restore] Telegram menolak data profil: %s", exc)
    except Exception as exc:
        errors.append(f"data profil ({_telegram_error(exc)})")
        log.exception("[Restore] Gagal memulihkan data profil: %s", exc)

    photo_file = backup.get("photo_file")
    try:
        if photo_file:
            if not os.path.exists(BACKUP_PHOTO_PATH):
                raise FileNotFoundError("file foto backup tidak ditemukan")
            with open(BACKUP_PHOTO_PATH, "rb") as photo:
                await client.set_profile_photo(photo=photo)
        else:
            await _remove_current_photo(client)
    except RPCError as exc:
        errors.append(f"foto ({_telegram_error(exc)})")
        log.exception("[Restore] Telegram menolak foto backup: %s", exc)
    except Exception as exc:
        errors.append(f"foto ({_telegram_error(exc)})")
        log.exception("[Restore] Gagal memulihkan foto backup: %s", exc)

    if errors:
        return False, f"Profil dipulihkan sebagian. Alasan: {'; '.join(errors)}."
    return True, ""


def setup(client):
    """Daftarkan command .restore."""

    @client.on_message(dynamic_command("restore") & filters.me)
    async def cmd_restore(client, message):
        chat_id = message.chat.id
        success, detail = await restore_profile(client)
        if not success:
            await _notify(client, chat_id, f"❌ {detail}")
            return
        success_text = (
            "✅ RESTORE BERHASIL\n\n"
            "Profil berhasil dikembalikan.\n\n"
            "⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
        )
        try:
            success_message = await send_ui(client, chat_id, success_text)
        except Exception as exc:
            log.exception("[Restore] Gagal mengirim pesan sukses: %s", exc)
            success_message = None
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        if success_message is not None:
            asyncio.create_task(
                auto_delete(
                    success_message,
                    delay=AUTO_DELETE_CMD,
                    force=True,
                )
            )
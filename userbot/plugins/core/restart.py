"""
IBEKS USERBOT - Plugin: restart
Command: .restart
Merestart userbot dan mengirim notifikasi setelah hidup kembali.
"""

import asyncio
import os
import sys

from pyrogram import filters

from config import AUTO_DELETE_CMD, MAIN_FILE, RESTART_STATE_FILE
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from plugins.utils.ui import send_ui


def setup(client):
    """Daftarkan handler .restart pada instance client."""

    @client.on_message(dynamic_command("restart") & filters.me)
    async def cmd_restart(client, message):
        """Handler command .restart"""
        chat_id = message.chat.id
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        # Simpan chat_id agar bot bisa mengirim pesan setelah restart
        try:
            with open(RESTART_STATE_FILE, "w", encoding="utf-8") as f:
                f.write(str(chat_id))
        except Exception as exc:
            from utils.logger import log
            log.warning(f"[Restart] Gagal menyimpan state restart: {exc}")

        await send_ui(client, chat_id, "🔄 Userbot sedang direstart...", expandable=True)

        # Ganti proses saat ini dengan instance baru dari main.py
        try:
            os.execv(sys.executable, [sys.executable, MAIN_FILE])
        except Exception as exc:
            from utils.logger import log
            log.exception(f"[Restart] Gagal restart: {exc}")
            await send_ui(client, chat_id, "❌ Gagal merestart userbot.", expandable=True)

"""
IBEKS USERBOT - Plugin: setprefix
Command: .setprefix <new_prefix>
Mengubah prefix command dan menyimpannya di SQLite.
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.prefix_manager import set_prefix, is_valid_prefix
from plugins.utils.ui import send_ui


def setup(client):
    """Daftarkan handler .setprefix pada instance client."""

    @client.on_message(dynamic_command("setprefix") & filters.me)
    async def cmd_setprefix(client, message):
        """Handler command .setprefix"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        text = (message.text or message.caption or "").strip()

        # Ambil prefix baru dari command
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await send_ui(client, chat_id, "Gunakan: `.setprefix <prefix>`", "SETPREFIX", "CORE", "ERROR", expandable=True)
            return

        new_prefix = parts[1].strip()
        if not is_valid_prefix(new_prefix):
            await send_ui(client, chat_id, "Prefix tidak valid. Maksimal 4 karakter non-spasi.", "SETPREFIX", "CORE", "ERROR", expandable=True)
            return

        set_prefix(new_prefix)
        await send_ui(client, chat_id, f"Prefix berhasil diubah menjadi `{new_prefix}`", "SETPREFIX", "CORE", "SUCCESS", expandable=True)

"""
IBEKS USERBOT - Admin: Purge
Command: .purge (reply ke pesan paling awal yang ingin dihapus)
Menghapus semua pesan dari reply target hingga command .purge.
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.admin_helper import (
    admin_error_message,
    check_userbot_rights,
    is_group,
)
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.logger import log
from plugins.utils.ui import send_ui


def setup(client):
    @client.on_message(dynamic_command("purge") & filters.me)
    async def cmd_purge(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await send_ui(client, chat.id, "❌ Perintah ini hanya bisa digunakan di grup.", expandable=True)
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_delete_messages")
        if not ok:
            await send_ui(client, chat.id, err, "PURGE", "ADMIN", "ERROR", expandable=True)
            return

        if not message.reply_to_message:
            await send_ui(client, chat.id, "❌ Reply ke pesan paling awal yang ingin dihapus.", expandable=True)
            return

        start_id = message.reply_to_message.id
        end_id = message.id
        if start_id > end_id:
            await send_ui(client, chat.id, "❌ Rentang pesan tidak valid.", expandable=True)
            return

        try:
            message_ids = list(range(start_id, end_id + 1))
            await client.delete_messages(chat.id, message_ids)
            await send_ui(client, chat.id, f"✅ Berhasil menghapus {len(message_ids)} pesan.", expandable=True)
        except Exception as exc:
            log.exception(f"[Admin:Purge] Gagal purge pesan: {exc}")
            await send_ui(client, chat.id, admin_error_message(exc), "PURGE", "ADMIN", "ERROR", expandable=True)

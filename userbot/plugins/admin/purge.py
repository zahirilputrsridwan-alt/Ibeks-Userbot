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


def setup(client):
    @client.on_message(dynamic_command("purge") & filters.me)
    async def cmd_purge(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await client.send_message(chat.id, "❌ Perintah ini hanya bisa digunakan di grup.")
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_delete_messages")
        if not ok:
            await client.send_message(chat.id, err)
            return

        if not message.reply_to_message:
            await client.send_message(chat.id, "❌ Reply ke pesan paling awal yang ingin dihapus.")
            return

        start_id = message.reply_to_message.id
        end_id = message.id
        if start_id > end_id:
            await client.send_message(chat.id, "❌ Rentang pesan tidak valid.")
            return

        try:
            message_ids = list(range(start_id, end_id + 1))
            await client.delete_messages(chat.id, message_ids)
            await client.send_message(
                chat.id,
                f"✅ Berhasil menghapus {len(message_ids)} pesan.",
            )
        except Exception as exc:
            log.exception(f"[Admin:Purge] Gagal purge pesan: {exc}")
            await client.send_message(chat.id, admin_error_message(exc))

"""
IBEKS USERBOT - Admin: Pin
Command: .pin (reply ke pesan yang akan dipin)
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
    @client.on_message(dynamic_command("pin") & filters.me)
    async def cmd_pin(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await client.send_message(chat.id, "❌ Perintah ini hanya bisa digunakan di grup.")
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_pin_messages")
        if not ok:
            await client.send_message(chat.id, err)
            return

        if not message.reply_to_message:
            await client.send_message(chat.id, "❌ Reply ke pesan yang ingin dipin.")
            return

        try:
            await client.pin_chat_message(
                chat.id,
                message.reply_to_message.id,
                disable_notification=False,
            )
            await client.send_message(chat.id, "✅ Pesan berhasil dipin.")
        except Exception as exc:
            log.exception(f"[Admin:Pin] Gagal pin pesan: {exc}")
            await client.send_message(chat.id, admin_error_message(exc))

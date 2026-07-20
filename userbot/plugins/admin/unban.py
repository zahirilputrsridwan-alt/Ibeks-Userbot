"""
IBEKS USERBOT - Admin: Unban
Command: .unban (reply | username | id)
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.admin_helper import (
    admin_error_message,
    check_userbot_rights,
    get_target_user,
    is_group,
)
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.logger import log


def setup(client):
    @client.on_message(dynamic_command("unban") & filters.me)
    async def cmd_unban(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await client.send_message(chat.id, "❌ Perintah ini hanya bisa digunakan di grup.")
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_restrict_members")
        if not ok:
            await client.send_message(chat.id, err)
            return

        target_id = await get_target_user(client, message)
        if not target_id:
            await client.send_message(
                chat.id,
                "❌ Target tidak ditemukan. Reply ke pesan user atau berikan username/ID.",
            )
            return

        try:
            await client.unban_chat_member(chat.id, target_id)
            await client.send_message(chat.id, "✅ User berhasil diunban.")
        except Exception as exc:
            log.exception(f"[Admin:Unban] Gagal unban user {target_id}: {exc}")
            await client.send_message(chat.id, admin_error_message(exc))

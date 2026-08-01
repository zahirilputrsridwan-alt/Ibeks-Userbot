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
from plugins.utils.ui import send_ui


def setup(client):
    @client.on_message(dynamic_command("unban") & filters.me)
    async def cmd_unban(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await send_ui(client, chat.id, "Perintah ini hanya bisa digunakan di grup.", "UNBAN", "ADMIN", "ERROR", expandable=True)
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_restrict_members")
        if not ok:
            await send_ui(client, chat.id, err, "UNBAN", "ADMIN", "ERROR", expandable=True)
            return

        target_id = await get_target_user(client, message)
        if not target_id:
            await send_ui(client, chat.id, "Target tidak ditemukan. Reply ke pesan user atau berikan username/ID.", "UNBAN", "ADMIN", "ERROR", expandable=True)
            return

        try:
            await client.unban_chat_member(chat.id, target_id)
            await send_ui(client, chat.id, "User berhasil diunban.", "UNBAN", "ADMIN", "SUCCESS", expandable=True)
        except Exception as exc:
            log.exception(f"[Admin:Unban] Gagal unban user {target_id}: {exc}")
            await send_ui(client, chat.id, admin_error_message(exc), "UNBAN", "ADMIN", "ERROR", expandable=True)

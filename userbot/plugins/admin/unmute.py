"""
IBEKS USERBOT - Admin: Unmute
Command: .unmute (reply | username | id)
"""

import asyncio
from datetime import datetime, timezone

from pyrogram import filters
from pyrogram.types import ChatPermissions

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
    @client.on_message(dynamic_command("unmute") & filters.me)
    async def cmd_unmute(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await send_ui(client, chat.id, "Perintah ini hanya bisa digunakan di grup.", "UNMUTE", "ADMIN", "ERROR", expandable=True)
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_restrict_members")
        if not ok:
            await send_ui(client, chat.id, err, "UNMUTE", "ADMIN", "ERROR", expandable=True)
            return

        target_id = await get_target_user(client, message)
        if not target_id:
            await send_ui(client, chat.id, "Target tidak ditemukan. Reply ke pesan user atau berikan username/ID.", "UNMUTE", "ADMIN", "ERROR", expandable=True)
            return

        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_send_polls=True,
            can_add_web_page_previews=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
        )

        try:
            await client.restrict_chat_member(
                chat.id,
                target_id,
                permissions,
                until_date=datetime.now(timezone.utc),
            )
            await send_ui(client, chat.id, "User berhasil diunmute.", "UNMUTE", "ADMIN", "SUCCESS", expandable=True)
        except Exception as exc:
            log.exception(f"[Admin:Unmute] Gagal unmute user {target_id}: {exc}")
            await send_ui(client, chat.id, admin_error_message(exc), "UNMUTE", "ADMIN", "ERROR", expandable=True)

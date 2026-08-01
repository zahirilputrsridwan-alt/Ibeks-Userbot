"""
IBEKS USERBOT - Admin: Demote
Command: .demote (reply | username | id)
"""

import asyncio

from pyrogram import filters
from pyrogram.types import ChatPrivileges

from config import AUTO_DELETE_CMD
from utils.admin_helper import (
    admin_error_message,
    check_userbot_rights,
    get_target_user,
    is_group,
    is_self_target_async,
)
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.logger import log
from plugins.utils.ui import send_ui


def setup(client):
    @client.on_message(dynamic_command("demote") & filters.me)
    async def cmd_demote(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await send_ui(client, chat.id, "Perintah ini hanya bisa digunakan di grup.", "DEMOTE", "ADMIN", "ERROR", expandable=True)
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_promote_members")
        if not ok:
            await send_ui(client, chat.id, err, "DEMOTE", "ADMIN", "ERROR", expandable=True)
            return

        target_id = await get_target_user(client, message)
        if not target_id:
            await send_ui(client, chat.id, "Target tidak ditemukan. Reply ke pesan user atau berikan username/ID.", "DEMOTE", "ADMIN", "ERROR", expandable=True)
            return

        if await is_self_target_async(client, target_id):
            await send_ui(client, chat.id, "Tidak bisa demote diri sendiri.", "DEMOTE", "ADMIN", "ERROR", expandable=True)
            return

        privileges = ChatPrivileges(
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_post_messages=False,
            can_edit_messages=False,
            is_anonymous=False,
        )

        try:
            await client.promote_chat_member(chat.id, target_id, privileges=privileges)
            await send_ui(client, chat.id, "Admin berhasil didemote.", "DEMOTE", "ADMIN", "SUCCESS", expandable=True)
        except Exception as exc:
            log.exception(f"[Admin:Demote] Gagal demote user {target_id}: {exc}")
            await send_ui(client, chat.id, admin_error_message(exc), "DEMOTE", "ADMIN", "ERROR", expandable=True)

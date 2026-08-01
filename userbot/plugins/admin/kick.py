"""
IBEKS USERBOT - Admin: Kick
Command: .kick (reply | username | id)
"""

import asyncio
from datetime import datetime, timedelta, timezone

from pyrogram import filters

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
    @client.on_message(dynamic_command("kick") & filters.me)
    async def cmd_kick(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await send_ui(client, chat.id, "❌ Perintah ini hanya bisa digunakan di grup.", expandable=True)
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_restrict_members")
        if not ok:
            await send_ui(client, chat.id, err, "KICK", "ADMIN", "ERROR", expandable=True)
            return

        target_id = await get_target_user(client, message)
        if not target_id:
            await send_ui(client, chat.id, "❌ Target tidak ditemukan. Reply ke pesan user atau berikan username/ID.", expandable=True)
            return

        if await is_self_target_async(client, target_id):
            await send_ui(client, chat.id, "❌ Tidak bisa kick diri sendiri.", expandable=True)
            return

        try:
            # Kick = banned sebentar (30 detik), lalu otomatis bisa join lagi
            until = datetime.now(timezone.utc) + timedelta(seconds=30)
            await client.ban_chat_member(chat.id, target_id, until_date=until)
            await send_ui(client, chat.id, "✅ User berhasil dikick dari grup.", expandable=True)
        except Exception as exc:
            log.exception(f"[Admin:Kick] Gagal kick user {target_id}: {exc}")
            await send_ui(client, chat.id, admin_error_message(exc), "KICK", "ADMIN", "ERROR", expandable=True)

"""
IBEKS USERBOT - Admin: Promote
Command: .promote (reply | username | id)
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
    @client.on_message(dynamic_command("promote") & filters.me)
    async def cmd_promote(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await send_ui(client, chat.id, "╭─「 ❌ 𝗣𝗥𝗢𝗠𝗢𝗧𝗘 」\n│\n├ 💬 𝗖𝗵𝗮𝘁\n│  ╰➤ Perintah ini hanya bisa digunakan di grup.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_promote_members")
        if not ok:
            await send_ui(client, chat.id, f"╭─「 ❌ 𝗣𝗥𝗢𝗠𝗢𝗧𝗘 」\n│\n├ 🔐 𝗛𝗮𝗸 𝗔𝗸𝘀𝗲𝘀\n│  ╰➤ {err}\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        target_id = await get_target_user(client, message)
        if not target_id:
            await send_ui(client, chat.id, "╭─「 ❌ 𝗣𝗥𝗢𝗠𝗢𝗧𝗘 」\n│\n├ 👤 𝗧𝗮𝗿𝗴𝗲𝘁\n│  ╰➤ Tidak ditemukan. Reply ke pesan user atau berikan username/ID.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        if await is_self_target_async(client, target_id):
            await send_ui(client, chat.id, "╭─「 ❌ 𝗣𝗥𝗢𝗠𝗢𝗧𝗘 」\n│\n├ 👤 𝗧𝗮𝗿𝗴𝗲𝘁\n│  ╰➤ Tidak bisa promote diri sendiri.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        privileges = ChatPrivileges(
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_promote_members=False,
            can_post_messages=False,
            can_edit_messages=False,
            is_anonymous=False,
        )

        try:
            await client.promote_chat_member(chat.id, target_id, privileges=privileges)
            await send_ui(client, chat.id, f"╭─「 ✅ 𝗣𝗥𝗢𝗠𝗢𝗧𝗘 」\n│\n├ 👤 𝗧𝗮𝗿𝗴𝗲𝘁\n│  ╰➤ `{target_id}`\n├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ Berhasil menjadi admin.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
        except Exception as exc:
            log.exception(f"[Admin:Promote] Gagal promote user {target_id}: {exc}")
            await send_ui(client, chat.id, f"╭─「 ❌ 𝗣𝗥𝗢𝗠𝗢𝗧𝗘 」\n│\n├ 👤 𝗧𝗮𝗿𝗴𝗲𝘁\n│  ╰➤ `{target_id}`\n├ ⚠️ 𝗘𝗿𝗿𝗼𝗿\n│  ╰➤ {admin_error_message(exc)}\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")

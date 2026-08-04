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
from plugins.utils.ui import send_ui


def setup(client):
    @client.on_message(dynamic_command("pin") & filters.me)
    async def cmd_pin(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await send_ui(client, chat.id, "╭─「 ❌ 𝗣𝗜𝗡 」\n│\n├ 💬 𝗖𝗵𝗮𝘁\n│  ╰➤ Perintah ini hanya bisa digunakan di grup.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_pin_messages")
        if not ok:
            await send_ui(client, chat.id, f"╭─「 ❌ 𝗣𝗜𝗡 」\n│\n├ 🔐 𝗛𝗮𝗸 𝗔𝗸𝘀𝗲𝘀\n│  ╰➤ {err}\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        if not message.reply_to_message:
            await send_ui(client, chat.id, "╭─「 ❌ 𝗣𝗜𝗡 」\n│\n├ 💬 𝗣𝗲𝘀𝗮𝗻\n│  ╰➤ Reply ke pesan yang ingin dipin.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        try:
            await client.pin_chat_message(
                chat.id,
                message.reply_to_message.id,
                disable_notification=False,
            )
            await send_ui(client, chat.id, "╭─「 ✅ 𝗣𝗜𝗡 」\n│\n├ 💬 𝗣𝗲𝘀𝗮𝗻\n│  ╰➤ Berhasil dipin.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
        except Exception as exc:
            log.exception(f"[Admin:Pin] Gagal pin pesan: {exc}")
            await send_ui(client, chat.id, f"╭─「 ❌ 𝗣𝗜𝗡 」\n│\n├ ⚠️ 𝗘𝗿𝗿𝗼𝗿\n│  ╰➤ {admin_error_message(exc)}\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")

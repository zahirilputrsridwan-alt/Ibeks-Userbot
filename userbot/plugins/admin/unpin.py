"""
IBEKS USERBOT - Admin: Unpin
Command: .unpin (reply ke pesan) atau .unpin tanpa reply untuk unpin semua.
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
    @client.on_message(dynamic_command("unpin") & filters.me)
    async def cmd_unpin(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await send_ui(client, chat.id, "╭─「 ❌ 𝗨𝗡𝗣𝗜𝗡 」\n│\n├ 💬 𝗖𝗵𝗮𝘁\n│  ╰➤ Perintah ini hanya bisa digunakan di grup.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_pin_messages")
        if not ok:
            await send_ui(client, chat.id, f"╭─「 ❌ 𝗨𝗡𝗣𝗜𝗡 」\n│\n├ 🔐 𝗛𝗮𝗸 𝗔𝗸𝘀𝗲𝘀\n│  ╰➤ {err}\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        try:
            if message.reply_to_message:
                await client.unpin_chat_message(chat.id, message.reply_to_message.id)
                await send_ui(client, chat.id, "╭─「 ✅ 𝗨𝗡𝗣𝗜𝗡 」\n│\n├ 💬 𝗣𝗲𝘀𝗮𝗻\n│  ╰➤ Berhasil diunpin.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            else:
                await client.unpin_all_chat_messages(chat.id)
                await send_ui(client, chat.id, "╭─「 ✅ 𝗨𝗡𝗣𝗜𝗡 」\n│\n├ 💬 𝗣𝗶𝗻\n│  ╰➤ Semua pin berhasil dilepas.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
        except Exception as exc:
            log.exception(f"[Admin:Unpin] Gagal unpin pesan: {exc}")
            await send_ui(client, chat.id, f"╭─「 ❌ 𝗨𝗡𝗣𝗜𝗡 」\n│\n├ ⚠️ 𝗘𝗿𝗿𝗼𝗿\n│  ╰➤ {admin_error_message(exc)}\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")

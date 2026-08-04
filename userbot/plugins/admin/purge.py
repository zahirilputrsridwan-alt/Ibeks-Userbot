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
from plugins.utils.ui import send_ui


def setup(client):
    @client.on_message(dynamic_command("purge") & filters.me)
    async def cmd_purge(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat = message.chat

        if not is_group(chat):
            await send_ui(client, chat.id, "╭─「 ❌ 𝗣𝗨𝗥𝗚𝗘 」\n│\n├ 💬 𝗖𝗵𝗮𝘁\n│  ╰➤ Perintah ini hanya bisa digunakan di grup.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        ok, err = await check_userbot_rights(client, chat.id, "can_delete_messages")
        if not ok:
            await send_ui(client, chat.id, f"╭─「 ❌ 𝗣𝗨𝗥𝗚𝗘 」\n│\n├ 🔐 𝗛𝗮𝗸 𝗔𝗸𝘀𝗲𝘀\n│  ╰➤ {err}\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        if not message.reply_to_message:
            await send_ui(client, chat.id, "╭─「 ❌ 𝗣𝗨𝗥𝗚𝗘 」\n│\n├ 💬 𝗣𝗲𝘀𝗮𝗻\n│  ╰➤ Reply ke pesan paling awal yang ingin dihapus.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        start_id = message.reply_to_message.id
        end_id = message.id
        if start_id > end_id:
            await send_ui(client, chat.id, "╭─「 ❌ 𝗣𝗨𝗥𝗚𝗘 」\n│\n├ 📏 𝗥𝗲𝗻𝘁𝗮𝗻𝗴\n│  ╰➤ Pesan tidak valid.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
            return

        try:
            message_ids = list(range(start_id, end_id + 1))
            await client.delete_messages(chat.id, message_ids)
            await send_ui(client, chat.id, f"╭─「 ✅ 𝗣𝗨𝗥𝗚𝗘 」\n│\n├ 🗑 𝗝𝘂𝗺𝗹𝗮𝗵\n│  ╰➤ {len(message_ids)} pesan berhasil dihapus.\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
        except Exception as exc:
            log.exception(f"[Admin:Purge] Gagal purge pesan: {exc}")
            await send_ui(client, chat.id, f"╭─「 ❌ 𝗣𝗨𝗥𝗚𝗘 」\n│\n├ ⚠️ 𝗘𝗿𝗿𝗼𝗿\n│  ╰➤ {admin_error_message(exc)}\n│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")

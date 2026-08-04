"""
IBEKS USERBOT - Plugin: me
Command: .me
Menampilkan informasi akun Telegram yang sedang login.
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from plugins.utils.ui import send_ui


def setup(client):
    """Daftarkan handler .me pada instance client."""

    @client.on_message(dynamic_command("me") & filters.me)
    async def cmd_me(client, message):
        """Handler command .me"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        me = await client.get_me()
        name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "Unknown"
        username = f"@{me.username}" if me.username else "Tidak ada"
        premium = "Ya" if getattr(me, "is_premium", False) else "Tidak"
        dc_id = getattr(me, "dc_id", None) or "Tidak tersedia"
        await send_ui(
            client,
            message.chat.id,
            (
                "╭─「 👤 𝗔𝗞𝗨𝗡 𝗦𝗔𝗬𝗔 」\n│\n"
                f"├ 👤 𝗡𝗮𝗺𝗮\n│  ╰➤ `{name}`\n"
                f"├ 🔗 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲\n│  ╰➤ `{username}`\n"
                f"├ 🆔 𝗨𝘀𝗲𝗿 𝗜𝗗\n│  ╰➤ `{me.id}`\n"
                f"├ ⭐ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺\n│  ╰➤ `{premium}`\n"
                f"├ 🌐 𝗗𝗖 𝗜𝗗\n│  ╰➤ `{dc_id}`\n"
                "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
            ),
            expandable=True,
            disable_web_page_preview=True,
        )

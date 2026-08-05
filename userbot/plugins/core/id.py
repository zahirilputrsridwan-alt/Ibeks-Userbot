"""IBEKS USERBOT - Plugin: id.

Command: .id
Menampilkan informasi akun sendiri atau akun pada pesan yang direply.
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from plugins.utils.ui import send_ui


def _display_name(user) -> str:
    """Gabungkan nama depan/belakang tanpa menghasilkan spasi kosong."""
    first_name = getattr(user, "first_name", None) or ""
    last_name = getattr(user, "last_name", None) or ""
    return " ".join(part for part in (first_name, last_name) if part).strip() or "Tidak diketahui"


def _username(user) -> str:
    username = getattr(user, "username", None)
    return f"@{username}" if username else "Tidak ada"


def setup(client):
    """Daftarkan handler .id pada instance client."""

    @client.on_message(dynamic_command("id") & filters.me)
    async def cmd_id(client, message):
        """Handler command .id"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        reply = message.reply_to_message
        target = reply.from_user if reply else message.from_user
        if target is None:
            target = await client.get_me()

        target_type = "Bot" if getattr(target, "is_bot", False) else "User"
        target_name = _display_name(target)
        target_username = _username(target)
        target_id = getattr(target, "id", "Tidak diketahui")
        chat_id = message.chat.id if message.chat else "Tidak diketahui"

        await send_ui(
            client,
            chat_id,
            (
                "╭─「 🆔 𝗜𝗗𝗘𝗡𝗧𝗜𝗧𝗔𝗦 」\n│\n"
                f"├ 👤 𝗡𝗮𝗺𝗮\n│  ╰➤ {target_name}\n"
                f"├ 📛 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲\n│  ╰➤ {target_username}\n"
                f"├ 🆔 𝗨𝘀𝗲𝗿 𝗜𝗗\n│  ╰➤ `{target_id}`\n"
                f"├ 🤖 𝗧𝗶𝗽𝗲\n│  ╰➤ {target_type}\n"
                f"├ 💬 𝗖𝗵𝗮𝘁 𝗜𝗗\n│  ╰➤ `{chat_id}`\n"
                "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
            ),
            expandable=True,
        )

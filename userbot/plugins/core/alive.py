"""
IBEKS USERBOT - Plugin: alive
Command: .alive
Menampilkan status online bot beserta info versi dan owner.

Flow:
1. Hapus pesan command asli.
2. Kirim pesan baru sebagai response.
"""

import asyncio
import sys

import pyrogram
from pyrogram import filters

from config import BOT_NAME, VERSION, AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from plugins.utils.ui import send_ui


def setup(client):
    """Daftarkan handler .alive pada instance client."""

    @client.on_message(dynamic_command("alive") & filters.me)
    async def cmd_alive(client, message):
        """Handler command .alive"""
        # Hapus pesan command asli
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        me = await client.get_me()
        owner = me.first_name or me.username or "Unknown"
        python_ver = sys.version.split()[0]
        pyrogram_ver = pyrogram.__version__

        text = (
            f"╭─「 🟢 𝗔𝗟𝗜𝗩𝗘 」\n│\n"
            f"├ 🤖 𝗕𝗼𝘁\n│  ╰➤ `{BOT_NAME}`\n"
            "├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ `Online`\n"
            f"├ 📦 𝗩𝗲𝗿𝘀𝗶\n│  ╰➤ `{VERSION}`\n"
            f"├ 🐍 𝗣𝘆𝘁𝗵𝗼𝗻\n│  ╰➤ `{python_ver}`\n"
            f"├ ⚙️ 𝗣𝘆𝗿𝗼𝗴𝗿𝗮𝗺\n│  ╰➤ `{pyrogram_ver}`\n"
            f"├ 👤 𝗢𝘄𝗻𝗲𝗿\n│  ╰➤ `{owner}`\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
        )
        await send_ui(client, message.chat.id, text, expandable=True)

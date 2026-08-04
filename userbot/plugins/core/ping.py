"""
IBEKS USERBOT - Plugin: ping
Command: .ping
Menampilkan status bot, uptime, RAM, CPU, dan info owner.

Flow:
1. Hapus pesan command asli.
2. Kirim pesan baru sebagai response.
3. Edit response ke hasil akhir.
"""

import asyncio
import time

from pyrogram import filters

from config import BOT_NAME, VERSION, AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.helper import get_ram_usage, get_cpu_usage
from utils.uptime import format_uptime
from utils.filters import dynamic_command
from plugins.utils.ui import edit_ui, send_ui


def setup(client):
    """Daftarkan handler .ping pada instance client."""

    @client.on_message(dynamic_command("ping") & filters.me)
    async def cmd_ping(client, message):
        """Handler command .ping"""
        # Hapus pesan command asli
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id

        # Ukur ping lokal (waktu kirim pesan "loading")
        t_start = time.monotonic()
        sent = await send_ui(
            client,
            chat_id,
            "╭─「 🏓 𝗣𝗜𝗡𝗚 」\n│\n"
            "├ ⏱ 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ Mengukur ping...\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
            expandable=True,
        )
        ping_ms = round((time.monotonic() - t_start) * 1000, 2)

        # Ukur API ping via get_me()
        api_start = time.monotonic()
        me = await client.get_me()
        api_ping_ms = round((time.monotonic() - api_start) * 1000, 2)

        # Ambil nama owner
        owner = me.first_name or me.username or "Unknown"

        # Statistik sistem
        ram = get_ram_usage()
        cpu = get_cpu_usage()
        uptime = format_uptime()

        text = (
            "╭─「 🏓 𝗦𝗧𝗔𝗧𝗨𝗦 」\n"
            "│\n"
            f"├ 🏓 𝗣𝗶𝗻𝗴\n│  ╰➤ `{ping_ms} ms`\n"
            f"├ ⚡ 𝗔𝗣𝗜 𝗣𝗶𝗻𝗴\n│  ╰➤ `{api_ping_ms} ms`\n"
            f"├ ⏰ 𝗨𝗽𝘁𝗶𝗺𝗲\n│  ╰➤ `{uptime}`\n"
            f"├ 💾 𝗥𝗔𝗠\n│  ╰➤ `{ram}%`\n"
            f"├ 🖥 𝗖𝗣𝗨\n│  ╰➤ `{cpu}%`\n"
            f"├ 👤 𝗢𝘄𝗻𝗲𝗿\n│  ╰➤ `{owner}`\n"
            f"├ 🤖 𝗕𝗼𝘁\n│  ╰➤ `{BOT_NAME}`\n"
            f"├ 📦 𝗩𝗲𝗿𝘀𝗶𝗼𝗻\n│  ╰➤ `{VERSION}`\n"
            "│\n"
            "╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
        )
        try:
            await edit_ui(client, sent, text)
        except Exception:
            pass

"""
IBEKS USERBOT - Plugin: me
Command: .me
Menampilkan informasi akun Telegram yang sedang login.
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.formatter import format_me_info
from utils.filters import dynamic_command
from plugins.utils.ui import send_ui


def setup(client):
    """Daftarkan handler .me pada instance client."""

    @client.on_message(dynamic_command("me") & filters.me)
    async def cmd_me(client, message):
        """Handler command .me"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        me = await client.get_me()
        await send_ui(client, message.chat.id, format_me_info(me), "INFO AKUN", "CORE", "INFO", expandable=True)

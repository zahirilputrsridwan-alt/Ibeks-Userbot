"""
IBEKS USERBOT - Plugin: id
Command: .id
Menampilkan informasi user (target reply atau akun sendiri).
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.formatter import format_user_info
from utils.filters import dynamic_command


def setup(client):
    """Daftarkan handler .id pada instance client."""

    @client.on_message(dynamic_command("id") & filters.me)
    async def cmd_id(client, message):
        """Handler command .id"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        target = message.reply_to_message.from_user if message.reply_to_message else message.from_user

        await client.send_message(
            chat_id,
            format_user_info(target, chat_id=chat_id),
            disable_web_page_preview=True,
        )

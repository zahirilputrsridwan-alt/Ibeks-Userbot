"""
IBEKS USERBOT - Plugin: Voice Chat - Join VC
Command: .joinvc
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.formatter import format_status
from utils.voice_manager import voice_manager


def setup(client):
    """Daftarkan handler .joinvc."""
    voice_manager.set_client(client)

    @client.on_message(dynamic_command("joinvc") & filters.me)
    async def cmd_joinvc(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat_id = message.chat.id

        success, text = await voice_manager.join(chat_id)
        await client.send_message(chat_id, text)

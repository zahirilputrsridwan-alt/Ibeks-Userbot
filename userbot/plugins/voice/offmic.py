"""
IBEKS USERBOT - Plugin: Voice Chat - Off Mic
Command: .offmic
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.voice_manager import voice_manager


def setup(client):
    """Daftarkan handler .offmic."""
    voice_manager.set_client(client)

    @client.on_message(dynamic_command("offmic") & filters.me)
    async def cmd_offmic(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat_id = message.chat.id

        success, text = await voice_manager.set_mute(chat_id, muted=True)
        await client.send_message(chat_id, text)

"""
IBEKS USERBOT - Plugin: Voice Chat - Leave VC
Command: .leavevc
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.voice_manager import voice_manager
from plugins.utils.ui import send_ui


def setup(client):
    """Daftarkan handler .leavevc."""
    voice_manager.set_client(client)

    @client.on_message(dynamic_command("leavevc") & filters.me)
    async def cmd_leavevc(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        chat_id = message.chat.id

        success, text = await voice_manager.leave(chat_id)
        await send_ui(client, chat_id, text, "VOICE", "VOICE", "INFO", expandable=True)

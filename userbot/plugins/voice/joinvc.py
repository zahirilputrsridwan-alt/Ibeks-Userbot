"""
IBEKS USERBOT - Plugin: Voice Chat - Join VC
Command: .joinvc
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.voice_manager import voice_manager
from plugins.utils.ui import send_ui


def setup(client):
    """Daftarkan handler .joinvc."""
    voice_manager.set_client(client)

    @client.on_message(dynamic_command("joinvc") & filters.me)
    async def cmd_joinvc(client, message):
        chat_id = message.chat.id

        success, text = await voice_manager.join(chat_id)
        result = await send_ui(client, chat_id, text, "VOICE", "VOICE", "INFO", expandable=True)

        # Hapus command dan hasilnya setelah jeda
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        asyncio.create_task(auto_delete(result, delay=AUTO_DELETE_CMD))

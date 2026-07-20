"""
IBEKS USERBOT - Plugin: alive
Command: .alive
Menampilkan status online bot beserta info versi dan owner.
"""

import asyncio
import sys

import pyrogram
from pyrogram import filters

from config import BOT_NAME, VERSION, AUTO_DELETE_CMD, CMD_PREFIX
from utils.autodelete import auto_delete


def setup(client):
    """Daftarkan handler .alive pada instance client."""

    @client.on_message(filters.command("alive", prefixes=CMD_PREFIX) & filters.me)
    async def cmd_alive(client, message):
        """Handler command .alive"""
        me = await client.get_me()
        owner = me.first_name or me.username or "Unknown"
        python_ver = sys.version.split()[0]
        pyrogram_ver = pyrogram.__version__

        text = (
            f"🟢 **{BOT_NAME}**\n\n"
            f"**Status**   : `Online`\n"
            f"**Version**  : `{VERSION}`\n"
            f"**Python**   : `{python_ver}`\n"
            f"**Pyrogram** : `{pyrogram_ver}`\n"
            f"**Owner**    : `{owner}`"
        )

        await message.edit(text)

        # Hapus pesan command asli
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

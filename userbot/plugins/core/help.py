"""IBEKS USERBOT - Inline Help UI.

Command: .help
Navigasi kategori dilakukan dengan edit pesan dan CallbackQueryHandler.
"""

from __future__ import annotations

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.help_request import request_help
from utils.prefix_manager import get_prefix


async def _owner_name(client) -> str:
    user = await client.get_me()
    return user.first_name or user.username or str(user.id)


def setup(client):
    """Daftarkan command .help dan callback inline help."""

    @client.on_message(dynamic_command("help") & filters.me)
    async def cmd_help(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        owner_user = await client.get_me()
        request_help(
            chat_id=message.chat.id,
            user_id=owner_user.id,
            owner=await _owner_name(client),
            prefix=get_prefix(),
        )

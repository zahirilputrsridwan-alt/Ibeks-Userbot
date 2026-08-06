"""Registration entry point for the .panel command and callbacks."""

from __future__ import annotations

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from plugins.utils.ui import send_ui
from utils.autodelete import auto_delete
from utils.filters import dynamic_command

from . import callbacks, views
from .utils import is_owner


def register(client) -> None:
    @client.on_message(dynamic_command("panel"))
    async def panel_command(_client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        if not is_owner(message):
            await message.reply("❌ Anda tidak memiliki akses.")
            return
        text, markup = views.home(message)
        await send_ui(
            _client,
            message.chat.id,
            text,
            reply_markup=markup,
        )

    @client.on_callback_query(filters.regex(r"^ibp:"))
    async def panel_callback(_client, query):
        await callbacks.handle(query)
"""IBEKS USERBOT - Inline Help UI.

Command: .help
Navigasi kategori dilakukan dengan edit pesan dan CallbackQueryHandler.
"""

from __future__ import annotations

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from plugins.utils.ui import send_ui
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.help_builder import (
    build_home_text,
    get_plan,
    home_keyboard,
    page_count,
    scan_plugins,
    total_plugins,
)
from utils.help_callbacks import register_help_callbacks
from utils.prefix_manager import get_prefix


async def _owner_name(client) -> str:
    user = await client.get_me()
    return user.first_name or user.username or str(user.id)


def setup(client):
    """Daftarkan command .help dan callback inline help."""

    @client.on_message(dynamic_command("help") & filters.me)
    async def cmd_help(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        catalog = scan_plugins()
        owner_user = await client.get_me()
        text = build_home_text(
            plan=get_plan(owner_user.id),
            prefix=get_prefix(),
            plugins=total_plugins(catalog),
            owner=await _owner_name(client),
            page=0,
            pages=page_count(catalog),
        )
        await send_ui(
            client,
            message.chat.id,
            text,
            reply_markup=home_keyboard(catalog, 0),
        )

    register_help_callbacks(client)

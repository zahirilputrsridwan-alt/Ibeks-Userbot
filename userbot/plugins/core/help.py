"""
IBEKS USERBOT - Help Menu
Command: .help
Menu kategori dan command dibaca otomatis dari folder plugins/.
"""

from __future__ import annotations

import asyncio
import platform

import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import AUTO_DELETE_CMD, BOT_NAME, VERSION
from plugins.utils.help import category_commands, scan_plugins, total_commands
from plugins.utils.ui import edit_ui, send_ui
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.prefix_manager import get_prefix
from utils.uptime import format_uptime


CALLBACK_PREFIX = "ibeks_help:"


def _button(text: str, action: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=f"{CALLBACK_PREFIX}{action}")


def _home_keyboard(catalog: dict) -> InlineKeyboardMarkup:
    categories = [
        (category_key, plugins[0].category_name)
        for category_key, plugins in catalog.items()
        if plugins
    ]
    rows = [
        [_button(name, f"category:{category_key}") for category_key, name in categories[index:index + 2]]
        for index in range(0, len(categories), 2)
    ]
    rows.append([_button("🔄 Refresh", "refresh")])
    return InlineKeyboardMarkup(rows)


def _home_text(owner: str, catalog: dict) -> str:
    return (
        f"🤖 {BOT_NAME}\n\n"
        f"👤 Owner : {owner}\n"
        f"⚡ Prefix : {get_prefix()}\n"
        f"📦 Version : {VERSION}\n"
        f"🔌 Total Plugin : {sum(len(plugins) for plugins in catalog.values())}\n"
        f"⌨ Total Command : {total_commands(catalog)}\n"
        f"🐍 Python : {platform.python_version()}\n"
        f"🔥 Pyrogram : {pyrogram.__version__}\n"
        f"⏰ Uptime : {format_uptime()}"
    )


def _category_text(category_name: str, plugins: list) -> str:
    commands = category_commands(plugins)
    lines = [
        f"📂 {category_name.upper()}",
        "",
        f"📦 Jumlah Plugin : {len(plugins)}",
        f"⌨ Jumlah Command : {len(commands)}",
        "",
        "━━━━━━━━━━━━━━",
        "",
    ]
    lines.extend(f"• {get_prefix()}{command}" for command in commands)
    return "\n".join(lines)


def _category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            _button("⬅ Back", "home"),
            _button("🏠 Home", "home"),
        ]]
    )


async def _owner_name(client, message=None) -> str:
    user = getattr(message, "from_user", None)
    if user is None:
        user = await client.get_me()
    return user.first_name or user.username or "Unknown"


def setup(client):
    """Daftarkan handler command dan callback Help Menu."""

    @client.on_message(dynamic_command("help") & filters.me)
    async def cmd_help(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        catalog = scan_plugins()
        owner = await _owner_name(client, message)
        await send_ui(
            client,
            message.chat.id,
            _home_text(owner, catalog),
            reply_markup=_home_keyboard(catalog),
            expandable=True,
        )

    @client.on_callback_query(filters.regex(r"^ibeks_help:"))
    async def help_callback(client, query):
        data = query.data or ""
        if isinstance(data, bytes):
            data = data.decode(errors="ignore")
        action = data.removeprefix(CALLBACK_PREFIX)

        await query.answer()
        if not query.message:
            return

        catalog = scan_plugins()
        if action == "refresh" or action == "home":
            owner = await _owner_name(client, query.message)
            await edit_ui(
                client,
                query.message,
                _home_text(owner, catalog),
                reply_markup=_home_keyboard(catalog),
            )
            return

        if action.startswith("category:"):
            category_key = action.split(":", 1)[1]
            plugins = catalog.get(category_key)
            if not plugins:
                owner = await _owner_name(client, query.message)
                await edit_ui(
                    client,
                    query.message,
                    _home_text(owner, catalog),
                    reply_markup=_home_keyboard(catalog),
                )
                return

            await edit_ui(
                client,
                query.message,
                _category_text(plugins[0].category_name, plugins),
                reply_markup=_category_keyboard(),
            )
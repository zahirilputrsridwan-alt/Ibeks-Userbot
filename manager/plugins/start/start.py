"""Command /start dan menu utama Manager Bot."""

from __future__ import annotations

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import get_or_create_user
from formatter import full_name, guide_text, welcome_text
from logger import safe_handler


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📲 Minta Akses", callback_data="manager:request")],
            [
                InlineKeyboardButton("👤 Akun Saya", callback_data="manager:account"),
                InlineKeyboardButton("📖 Bantuan", callback_data="manager:help"),
            ],
            [InlineKeyboardButton("ℹ️ Tentang", callback_data="manager:about")],
        ]
    )


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Menu Utama", callback_data="manager:home")]]
    )


def setup(client):
    @client.on_message(filters.command("start") & filters.private)
    @safe_handler
    async def start_handler(client, message):
        user = message.from_user
        get_or_create_user(user.id, user.username, full_name(user))
        await message.reply(welcome_text(), reply_markup=main_keyboard())

    @client.on_callback_query(filters.regex(r"^manager:(home|request|help)$"))
    @safe_handler
    async def start_menu_callback(client, query):
        await query.answer()
        if not query.message:
            return
        action = query.data.rsplit(":", 1)[-1]
        if action == "home":
            await query.message.edit(welcome_text(), reply_markup=main_keyboard())
        elif action == "request":
            await query.message.edit(
                "📲 **Minta Akses**\n\n"
                "Permintaan akses akan tersedia pada tahap berikutnya.",
                reply_markup=home_keyboard(),
            )
        else:
            await query.message.edit(guide_text(), reply_markup=home_keyboard())

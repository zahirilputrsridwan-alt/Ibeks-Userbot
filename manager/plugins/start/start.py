"""Command /start dan menu utama Manager Bot."""

from __future__ import annotations

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import get_or_create_user
from admin import is_owner
from formatter import full_name, guide_text, welcome_text
from logger import log, safe_handler


def main_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    rows = [
            [InlineKeyboardButton("📲 Minta Akses", callback_data="manager:request")],
            [
                InlineKeyboardButton("👤 Akun Saya", callback_data="manager:account"),
                InlineKeyboardButton("📖 Bantuan", callback_data="manager:help"),
            ],
            [InlineKeyboardButton("ℹ️ Tentang", callback_data="manager:about")],
    ]
    if user_id is not None and is_owner(user_id):
        rows.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="manager:admin")])
    return InlineKeyboardMarkup(rows)


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Menu Utama", callback_data="manager:home")]]
    )


def setup(client):
    @client.on_message(filters.command("start") & filters.private, group=-100)
    @safe_handler
    async def start_handler(client, message):
        user = message.from_user
        log.info(
            "Menerima /start dari user %s dalam chat %s.",
            user.id if user else "unknown",
            message.chat.id if message.chat else "unknown",
        )
        get_or_create_user(user.id, user.username, full_name(user))
        await message.reply(welcome_text(), reply_markup=main_keyboard(user.id))

    @client.on_callback_query(filters.regex(r"^manager:(home|help)$"))
    @safe_handler
    async def start_menu_callback(client, query):
        await query.answer()
        if not query.message:
            return
        action = query.data.rsplit(":", 1)[-1]
        if action == "home":
            await query.message.edit(
                welcome_text(),
                reply_markup=main_keyboard(query.from_user.id if query.from_user else None),
            )
        else:
            await query.message.edit(guide_text(), reply_markup=home_keyboard())

    log.info("✓ Handler /start terdaftar untuk chat private.")

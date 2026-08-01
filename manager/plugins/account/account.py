"""Menu informasi akun pengguna."""

from __future__ import annotations

from pyrogram import filters

from database import get_or_create_user
from formatter import account_text, full_name
from logger import safe_handler
from plugins.start.start import home_keyboard


def setup(client):
    @client.on_callback_query(filters.regex(r"^manager:account$"))
    @safe_handler
    async def account_callback(client, query):
        await query.answer()
        if not query.message or not query.from_user:
            return
        user = query.from_user
        data = get_or_create_user(user.id, user.username, full_name(user))
        await query.message.edit(account_text(data), reply_markup=home_keyboard())

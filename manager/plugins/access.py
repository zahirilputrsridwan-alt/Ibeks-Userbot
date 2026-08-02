"""Placeholder menu Minta Akses untuk tahap berikutnya."""

from __future__ import annotations

from pyrogram import filters

from logger import safe_handler
from plugins.start.start import home_keyboard


def setup(client):
    @client.on_callback_query(filters.regex(r"^manager:request$"))
    @safe_handler
    async def request_access_callback(client, query):
        await query.answer()
        if query.message:
            await query.message.edit(
                "📲 Minta Akses\n\n"
                "Fitur akses akan tersedia pada tahap berikutnya.",
                reply_markup=home_keyboard(),
            )
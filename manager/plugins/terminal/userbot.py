"""Tombol kontrol lifecycle Userbot."""

from __future__ import annotations

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import get_user
from engine import (
    OFFLINE,
    ONLINE,
    STOPPED,
    ensure_supervisor,
    restart_userbot,
    start_userbot,
    stop_userbot,
    status_for,
)
from formatter import account_text, userbot_status_text
from logger import log, safe_handler
from plugins.start.start import home_keyboard


def userbot_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("▶ Start Userbot", callback_data="manager:userbot_start"),
                InlineKeyboardButton("⏹ Stop Userbot", callback_data="manager:userbot_stop"),
            ],
            [
                InlineKeyboardButton("🔄 Restart Userbot", callback_data="manager:userbot_restart"),
                InlineKeyboardButton("📊 Status Userbot", callback_data="manager:userbot_status"),
            ],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="manager:home")],
        ]
    )


def account_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("▶ Start Userbot", callback_data="manager:userbot_start"),
                InlineKeyboardButton("⏹ Stop Userbot", callback_data="manager:userbot_stop"),
            ],
            [
                InlineKeyboardButton("🔄 Restart Userbot", callback_data="manager:userbot_restart"),
                InlineKeyboardButton("📊 Status Userbot", callback_data="manager:userbot_status"),
            ],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="manager:home")],
        ]
    )


async def _refresh_account(query) -> None:
    user = get_user(query.from_user.id)
    if not user:
        return
    await query.message.edit(account_text(user), reply_markup=account_keyboard())


def setup(client):
    @client.on_callback_query(filters.regex(r"^manager:userbot_(start|stop|restart|status)$"))
    @safe_handler
    async def userbot_callback(client, query):
        await query.answer()
        if not query.from_user or not query.message:
            return
        user_id = query.from_user.id
        action = query.data.rsplit("_", 1)[-1]
        if action == "start":
            success, result = await start_userbot(user_id)
            ensure_supervisor(user_id)
        elif action == "stop":
            success, result = await stop_userbot(user_id)
        elif action == "restart":
            success, result = await restart_userbot(user_id)
            ensure_supervisor(user_id)
        else:
            user = get_user(user_id)
            if not user:
                return
            user["userbot_status"] = status_for(user_id)
            await query.message.edit(
                userbot_status_text(user),
                reply_markup=account_keyboard(),
            )
            return

        log.info(
            "Userbot action=%s user=%s success=%s result=%s",
            action,
            user_id,
            success,
            result,
        )
        user = get_user(user_id)
        if not user:
            return
        prefix = "✅" if success else "❌"
        await query.message.edit(
            f"{prefix} {result}\n\n{account_text(user)}",
            reply_markup=account_keyboard(),
        )
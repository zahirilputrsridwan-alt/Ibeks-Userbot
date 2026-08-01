"""Terminal relay Manager Bot <-> Userbot tanpa daftar command hardcode."""

from __future__ import annotations

import sqlite3

from pyrogram import filters

from config import USERBOT_RUNTIME_DIR
from database import get_user, get_user_by_userbot_id
from engine import is_running, mark_userbot_handshake
from logger import log, safe_handler

MANAGER_HANDSHAKE = "\u2063IBEKS_USERBOT_READY\u2063"


def _active_prefix(manager_user_id: int, userbot_id: int) -> str:
    """Baca prefix aktif langsung dari database runtime Userbot."""
    runtime_db = USERBOT_RUNTIME_DIR / str(manager_user_id) / "database.db"
    if not runtime_db.exists():
        return "."
    try:
        with sqlite3.connect(runtime_db, timeout=1) as connection:
            row = connection.execute(
                "SELECT prefix FROM settings WHERE telegram_id = ?",
                (userbot_id,),
            ).fetchone()
        return (row[0] if row and row[0] else ".")
    except sqlite3.Error as exc:
        log.warning("Gagal membaca prefix Userbot %s: %s", userbot_id, exc)
        return "."


def _command_filter(_, __, message) -> bool:
    """Cocokkan pesan pengguna berdasarkan prefix, bukan nama command."""
    if not message or not message.from_user:
        return False
    user = get_user(message.from_user.id)
    if not user or not user.get("userbot_telegram_id"):
        return False
    text = (message.text or message.caption or "").strip()
    prefix = _active_prefix(message.from_user.id, user["userbot_telegram_id"])
    return bool(text.startswith(prefix))


def _response_filter(_, __, message) -> bool:
    """Cocokkan seluruh output yang dikirim akun Userbot ke Manager Bot."""
    text = (message.text or message.caption or "").strip() if message else ""
    if text.startswith(MANAGER_HANDSHAKE):
        try:
            manager_user_id = int(text.removeprefix(MANAGER_HANDSHAKE))
        except ValueError:
            return False
        return bool(get_user(manager_user_id))
    return bool(
        message
        and message.from_user
        and get_user_by_userbot_id(message.from_user.id)
    )


async def _copy_command_to_userbot(client, message, user: dict) -> None:
    userbot_id = user["userbot_telegram_id"]
    reply_to_id = None

    if message.reply_to_message:
        forwarded = await client.forward_messages(
            userbot_id,
            message.chat.id,
            message.reply_to_message.id,
        )
        if isinstance(forwarded, list):
            forwarded = forwarded[0] if forwarded else None
        reply_to_id = getattr(forwarded, "id", None)

    text = message.text or message.caption or ""
    if message.media:
        await client.copy_message(
            userbot_id,
            message.chat.id,
            message.id,
            reply_to_message_id=reply_to_id,
        )
    else:
        await client.send_message(
            userbot_id,
            text,
            reply_to_message_id=reply_to_id,
        )


def setup(client):
    @client.on_message(
        filters.private
        & filters.incoming
        & filters.create(_response_filter, "UserbotResponse"),
        group=-1,
    )
    @safe_handler
    async def userbot_response_handler(client, message):
        """Salin semua tipe pesan output Userbot ke pengguna Manager."""
        handshake = (message.text or message.caption or "").strip()
        if handshake.startswith(MANAGER_HANDSHAKE):
            try:
                manager_user_id = int(handshake.removeprefix(MANAGER_HANDSHAKE))
            except ValueError:
                manager_user_id = 0
            if manager_user_id:
                mark_userbot_handshake(manager_user_id, message.from_user.id)
            return
        owner = get_user_by_userbot_id(message.from_user.id)
        if not owner:
            return
        try:
            await client.copy_message(
                owner["telegram_id"],
                message.chat.id,
                message.id,
            )
        except Exception as exc:
            log.exception(
                "Gagal meneruskan output Userbot %s ke %s: %s",
                message.from_user.id,
                owner["telegram_id"],
                exc,
            )

    @client.on_message(
        filters.private
        & filters.incoming
        & filters.create(_command_filter, "UserbotCommand"),
        group=-1,
    )
    @safe_handler
    async def terminal_command_handler(client, message):
        """Teruskan command ber-prefix tanpa mengetahui daftar plugin."""
        user = get_user(message.from_user.id)
        if not user or not user.get("userbot_telegram_id"):
            return
        if not is_running(message.from_user.id):
            await message.reply(
                "❌ Userbot sedang offline.\n\n"
                "Silakan hidupkan Userbot terlebih dahulu."
            )
            return
        try:
            await _copy_command_to_userbot(client, message, user)
        except Exception as exc:
            log.exception(
                "Gagal meneruskan command terminal user %s: %s",
                message.from_user.id,
                exc,
            )
            await message.reply("❌ Command gagal diteruskan ke Userbot.")
"""Terminal relay Manager Bot <-> Userbot tanpa daftar command hardcode."""

from __future__ import annotations

import sqlite3
import time

from pyrogram import filters

from config import USERBOT_RUNTIME_DIR
from database import get_user, get_user_by_userbot_id
from engine import is_running, mark_userbot_handshake
from logger import log, safe_handler
from membership import has_active_membership

MANAGER_HANDSHAKE = "\u2063IBEKS_USERBOT_READY\u2063"
_RECENT_COMMANDS: dict[tuple[int, str], float] = {}
_RECENT_RESPONSES: dict[tuple[int, int], float] = {}
_RECENT_RESPONSE_BODIES: dict[tuple[int, str], float] = {}
_FORWARDED_COMMAND_MESSAGES: set[tuple[int, int]] = set()
_DEDUPE_SECONDS = 30.0
_RESPONSE_BODY_DEDUPE_SECONDS = 10.0


def _is_duplicate(seen: dict, key) -> bool:
    now = time.monotonic()
    expired = [item for item, seen_at in seen.items()
               if now - seen_at > _DEDUPE_SECONDS]
    for item in expired:
        seen.pop(item, None)
    if key in seen:
        return True
    seen[key] = now
    return False


def _is_duplicate_response_body(userbot_id: int, message) -> bool:
    """Abaikan salinan output dengan message ID baru tetapi isi sama."""
    body = (message.text or message.caption or "").strip()
    if not body:
        return False
    now = time.monotonic()
    expired = [
        item for item, seen_at in _RECENT_RESPONSE_BODIES.items()
        if now - seen_at > _RESPONSE_BODY_DEDUPE_SECONDS
    ]
    for item in expired:
        _RECENT_RESPONSE_BODIES.pop(item, None)
    key = (userbot_id, body)
    if key in _RECENT_RESPONSE_BODIES:
        return True
    _RECENT_RESPONSE_BODIES[key] = now
    return False


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
    if not message or not message.from_user:
        return False
    if message.chat and (message.chat.id, message.id) in _FORWARDED_COMMAND_MESSAGES:
        return False
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
        response_key = (int(message.from_user.id), int(message.id))
        if _is_duplicate(_RECENT_RESPONSES, response_key):
            log.warning(
                "Output Userbot duplikat diabaikan: userbot=%s message=%s",
                response_key[0],
                response_key[1],
            )
            return
        if _is_duplicate_response_body(response_key[0], message):
            log.warning(
                "Output Userbot dengan isi sama diabaikan: userbot=%s",
                response_key[0],
            )
            return
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
        if owner.get("suspended"):
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
        group=-3,
    )
    @safe_handler
    async def terminal_command_handler(client, message):
        """Teruskan command ber-prefix tanpa mengetahui daftar plugin."""
        text = (message.text or message.caption or "").strip()
        reply_id = getattr(message.reply_to_message, "id", 0) or 0
        command_key = (int(message.chat.id), f"{reply_id}:{text}")
        if _is_duplicate(_RECENT_COMMANDS, command_key):
            log.warning(
                "Command terminal duplikat diabaikan: chat=%s command=%s",
                command_key[0],
                command_key[1],
            )
            return
        user = get_user(message.from_user.id)
        if not user or not user.get("userbot_telegram_id"):
            return
        if user.get("suspended"):
            await message.reply("❌ Akun Anda sedang disuspend oleh Admin.")
            return
        if not has_active_membership(user):
            await message.reply(
                "❌ Membership Anda telah berakhir. Silakan hubungi Admin."
            )
            return
        if not is_running(message.from_user.id):
            await message.reply(
                "❌ Userbot sedang offline.\n\n"
                "Silakan hidupkan Userbot terlebih dahulu."
            )
            return
        try:
            _FORWARDED_COMMAND_MESSAGES.add((message.chat.id, message.id))
            await _copy_command_to_userbot(client, message, user)
            # Owner dan Userbot dapat memakai akun Telegram yang sama.
            # Hapus command asli setelah berhasil disalin ke kanal Userbot
            # agar chat Owner tidak menampilkan command asli + salinannya.
            try:
                await message.delete()
            except Exception as exc:
                log.warning(
                    "Command sudah diteruskan tetapi pesan asli tidak dapat dihapus: %s",
                    exc,
                )
        except Exception as exc:
            log.exception(
                "Gagal meneruskan command terminal user %s: %s",
                message.from_user.id,
                exc,
            )
            await message.reply("❌ Command gagal diteruskan ke Userbot.")
"""
IBEKS USERBOT - PM Control + PMMSG + Tag Reply.

Commands:
  .pm all
  .pm contacts
  .pm nobody

  .pmmsg <pesan>
  .pmmsg status
  .pmmsg reset

  .tagreply on
  .tagreply off
  .tagreply set <pesan>
  .tagreply status
  .tagreply reset

PM Control tidak memblokir user Telegram.
Mode nobody/contacts bekerja dengan menghapus PM yang ditolak,
mengirim PMMSG, lalu menghentikan propagation agar plugin lain
tidak ikut memproses pesan tersebut.
"""

from __future__ import annotations

import time
from collections.abc import Iterable

from pyrogram import StopPropagation, filters
from pyrogram.enums import ChatType, MessageEntityType
from pyrogram.errors import Forbidden, FloodWait, RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db import ensure_user_settings, get_setting, set_setting
from plugins.utils.ui import send_ui
from utils.filters import dynamic_command
from utils.prefix_manager import get_owner_id, set_owner_id
from utils.logger import log


DEFAULT_PM_MODE = "all"
DEFAULT_PM_MESSAGE = "🚫 Maaf, saya sedang tidak menerima PM."
DEFAULT_TAGREPLY_MESSAGE = "Ada apa manggil-manggil saya? 😂"

TAGREPLY_COOLDOWN_SECONDS = 8.0
PM_REJECTION_COOLDOWN_SECONDS = 60.0

_last_tag_replies: dict[tuple[int, int], float] = {}
_last_pm_rejections: dict[tuple[int, int, str], float] = {}


def _command_args(message) -> list[str]:
    text = (message.text or message.caption or "").strip()
    return text.split(maxsplit=1)[1:] if text else []


def _command_payload(message) -> str:
    args = _command_args(message)
    return args[0].strip() if args else ""


async def _account_id(client) -> int:
    owner_id = get_owner_id()
    if owner_id:
        ensure_user_settings(int(owner_id))
        return int(owner_id)

    me = await client.get_me()
    owner_id = int(me.id)
    set_owner_id(owner_id)
    ensure_user_settings(owner_id)
    return owner_id


async def _is_privileged_sender(client, message, owner_id: int) -> bool:
    sender = getattr(message, "from_user", None)
    sender_id = int(getattr(sender, "id", 0) or 0)

    if not sender_id:
        return False

    if sender_id == owner_id:
        return True

    try:
        me = await client.get_me()
        return sender_id == int(me.id)
    except Exception:
        return False


async def _is_contact(client, user_id: int) -> bool:
    try:
        contacts = await client.get_contacts()
    except RPCError as exc:
        log.exception("[PMGate] get_contacts() failed: %s", exc)
        return False

    ids = set()

    if isinstance(contacts, Iterable):
        for item in contacts:
            uid = 0

            try:
                if getattr(item, "id", None) is not None:
                    uid = int(getattr(item, "id", 0) or 0)
                elif getattr(item, "user", None) is not None:
                    uid = int(getattr(item.user, "id", 0) or 0)
            except (TypeError, ValueError):
                uid = 0

            if uid:
                ids.add(uid)

    return user_id in ids


def _entity_mentions_username(message, username: str) -> bool:
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    username = username.casefold().lstrip("@")

    try:
        parsed = message.parse_entities()

        for entity, value in parsed.items():
            etype = getattr(entity, "type", None)

            if (
                etype == MessageEntityType.MENTION
                or str(etype).lower() == "mention"
            ):
                if str(value).casefold().lstrip("@") == username:
                    return True

    except Exception:
        for entity in entities:
            etype = getattr(entity, "type", None)

            if (
                etype == MessageEntityType.MENTION
                or str(etype).lower() == "mention"
            ):
                try:
                    offset = int(getattr(entity, "offset", 0) or 0)
                    length = int(getattr(entity, "length", 0) or 0)
                    value = text[offset : offset + length]
                except Exception:
                    continue

                if value.casefold().lstrip("@") == username:
                    return True

    return False


def _incoming_sender_id(message) -> int:
    sender = getattr(message, "from_user", None)
    try:
        return int(getattr(sender, "id", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _pm_control_text(mode: str, pmmsg: str) -> str:
    mode = mode.casefold()

    labels = {
        "all": "ALL",
        "contacts": "CONTACTS",
        "nobody": "NOBODY",
    }

    status = labels.get(mode, "ALL")

    return (
        "📩 PM CONTROL\n"
        "\n"
        "----------------------------------\n"
        f"🚫 MODE : {status}\n"
        f"✉️ PMMSG : {pmmsg}\n"
    )


def _pm_control_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🚫 NOBODY", callback_data="pmctl:nobody"),
                InlineKeyboardButton("👥 CONTACTS", callback_data="pmctl:contacts"),
                InlineKeyboardButton("✅ ALL", callback_data="pmctl:all"),
            ],
        ]
    )


def _pm_control_state(owner_id: int) -> tuple[str, str]:
    mode = str(
        get_setting(owner_id, "pm_mode", DEFAULT_PM_MODE)
        or DEFAULT_PM_MODE
    ).casefold()
    pmmsg = str(
        get_setting(
            owner_id,
            "pm_rejection_message",
            DEFAULT_PM_MESSAGE,
        )
        or DEFAULT_PM_MESSAGE
    )
    return mode, pmmsg


async def _send_pm_control(client, chat_id: int, owner_id: int) -> None:
    mode, pmmsg = _pm_control_state(owner_id)
    text = _pm_control_text(mode, pmmsg)

    try:
        await client.send_message(
            chat_id,
            text,
            reply_markup=_pm_control_keyboard(),
        )
    except TypeError:
        # Fallback kalau helper/client versi project tidak menerima markup.
        await send_ui(client, chat_id, text)


async def _edit_pm_control(client, panel_message, owner_id: int) -> None:
    mode, pmmsg = _pm_control_state(owner_id)
    await client.edit_message_text(
        panel_message.chat.id,
        panel_message.id,
        _pm_control_text(mode, pmmsg),
        reply_markup=_pm_control_keyboard(),
    )


def _is_pm_command(message) -> bool:
    text = (message.text or message.caption or "").strip().casefold()

    if not text:
        return False

    first = text.split(maxsplit=1)[0]
    first = first.split("@", 1)[0]

    return first in {
        ".pm",
        ".pmmsg",
        ".tagreply",
    }


def setup(client):
    """Register PM Control, PMMSG, dan Tag Reply."""

    # ---------------------------------------------------------
    # INCOMING PM GATE
    # ---------------------------------------------------------
    @client.on_message(filters.incoming & filters.private, group=-200)
    async def pm_gate(client, message):
        if getattr(message.chat, "type", None) != ChatType.PRIVATE:
            return

        owner_id = await _account_id(client)
        mode = str(
            get_setting(owner_id, "pm_mode", DEFAULT_PM_MODE)
            or DEFAULT_PM_MODE
        ).casefold()

        # ALL = PM normal.
        if mode == "all":
            return

        sender_id = _incoming_sender_id(message)

        if not sender_id:
            return

        # Jangan tolak pesan dari akun sendiri.
        if await _is_privileged_sender(client, message, owner_id):
            return

        # CONTACTS = kontak boleh masuk.
        if mode == "contacts":
            try:
                if await _is_contact(client, sender_id):
                    return
            except Exception as exc:
                log.exception(
                    "[PMGate] Contact check failed for %s: %s",
                    sender_id,
                    exc,
                )

        # NOBODY atau non-contact pada CONTACTS.
        try:
            try:
                await message.delete()
                log.info(
                    "[PMGate] Deleted incoming PM sender_id=%s message_id=%s",
                    sender_id,
                    getattr(message, "id", None),
                )
            except Exception as exc:
                log.exception(
                    "[PMGate] Failed deleting incoming PM sender_id=%s: %s",
                    sender_id,
                    exc,
                )

            rejection = str(
                get_setting(
                    owner_id,
                    "pm_rejection_message",
                    DEFAULT_PM_MESSAGE,
                )
                or DEFAULT_PM_MESSAGE
            )

            key = (owner_id, sender_id, mode)
            now = time.monotonic()
            last = _last_pm_rejections.get(key, 0.0)

            if now - last >= PM_REJECTION_COOLDOWN_SECONDS:
                try:
                    await client.send_message(sender_id, rejection)
                    _last_pm_rejections[key] = now
                except Exception as exc:
                    log.exception(
                        "[PMGate] Failed sending rejection to %s: %s",
                        sender_id,
                        exc,
                    )

        finally:
            # Sangat penting: plugin lain tidak boleh menerima PM yang ditolak.
            raise StopPropagation

    # ---------------------------------------------------------
    # OUTGOING OWNER PM GATE
    #
    # Saat nobody aktif, owner juga tidak bisa membalas user:
    # pesan outgoing private biasa dihapus.
    #
    # Command PM/PMMSG/TAGREPLY dikecualikan agar command tetap
    # bisa dijalankan dari private chat.
    # ---------------------------------------------------------
    @client.on_message(filters.outgoing & filters.private, group=-190)
    async def owner_pm_gate(client, message):
        if _is_pm_command(message):
            return

        owner_id = await _account_id(client)
        mode = str(
            get_setting(owner_id, "pm_mode", DEFAULT_PM_MODE)
            or DEFAULT_PM_MODE
        ).casefold()

        if mode == "all":
            return

        chat_id = int(getattr(message.chat, "id", 0) or 0)

        if not chat_id or chat_id == owner_id:
            return

        if mode == "contacts":
            try:
                if await _is_contact(client, chat_id):
                    return
            except Exception:
                pass

        try:
            await message.delete()
            log.info(
                "[PMGate] Deleted outgoing owner PM chat_id=%s mode=%s",
                chat_id,
                mode,
            )
        except Exception as exc:
            log.exception(
                "[PMGate] Failed deleting outgoing owner PM chat_id=%s: %s",
                chat_id,
                exc,
            )

    # ---------------------------------------------------------
    # TAG REPLY GATE
    # ---------------------------------------------------------
    @client.on_message(filters.incoming & filters.group, group=-80)
    async def tagreply_gate(client, message):
        if getattr(message.chat, "type", None) not in {
            ChatType.GROUP,
            ChatType.SUPERGROUP,
        }:
            return

        owner_id = await _account_id(client)

        if not bool(get_setting(owner_id, "tagreply_enabled", 0)):
            return

        sender = getattr(message, "from_user", None)
        sender_id = int(getattr(sender, "id", 0) or 0)

        if not sender_id:
            return

        if await _is_privileged_sender(client, message, owner_id):
            return

        me = await client.get_me()
        username = getattr(me, "username", None)

        if not username:
            return

        if not _entity_mentions_username(message, username):
            return

        if getattr(sender, "is_bot", False):
            return

        now = time.monotonic()
        key = (int(message.chat.id), sender_id)

        if now - _last_tag_replies.get(key, 0.0) < TAGREPLY_COOLDOWN_SECONDS:
            return

        _last_tag_replies[key] = now

        reply_text = str(
            get_setting(
                owner_id,
                "tagreply_message",
                DEFAULT_TAGREPLY_MESSAGE,
            )
            or DEFAULT_TAGREPLY_MESSAGE
        )

        try:
            await message.reply(reply_text)
        except (Forbidden, FloodWait):
            return
        except Exception:
            return

    # ---------------------------------------------------------
    # .PM
    # ---------------------------------------------------------
    @client.on_message(dynamic_command("pm") & filters.me, group=-150)
    async def cmd_pm(client, message):
        owner_id = await _account_id(client)
        mode = _command_payload(message).casefold()

        if mode not in {"all", "contacts", "nobody"}:
            await send_ui(
                client,
                message.chat.id,
                "❌ Gunakan:\n"
                ".pm all\n"
                ".pm contacts\n"
                ".pm nobody",
            )
            return

        set_setting(owner_id, "pm_mode", mode)

        labels = {
            "all": "SEMUA PM DITERIMA",
            "contacts": "HANYA KONTAK",
            "nobody": "NOBODY AKTIF",
        }

        await send_ui(
            client,
            message.chat.id,
            f"✅ PM Control berhasil diubah.\n"
            f"Mode: {labels[mode]}",
        )

        # Tampilkan status setelah command.
        await _send_pm_control(client, message.chat.id, owner_id)
        raise StopPropagation

    # ---------------------------------------------------------
    # PM CONTROL BUTTONS
    # ---------------------------------------------------------
    @client.on_callback_query(filters.regex(r"^pmctl:(all|contacts|nobody)$"))
    async def pm_control_callback(client, callback_query):
        owner_id = await _account_id(client)

        user = getattr(callback_query, "from_user", None)
        user_id = int(getattr(user, "id", 0) or 0)

        if user_id != owner_id:
            await callback_query.answer(
                "❌ Hanya owner yang bisa mengatur PM.",
                show_alert=True,
            )
            return

        mode = callback_query.data.split(":", 1)[1]
        set_setting(owner_id, "pm_mode", mode)

        await callback_query.answer(
            "PM Control berhasil diubah.",
            show_alert=False,
        )

        await _edit_pm_control(client, callback_query.message, owner_id)

    # ---------------------------------------------------------
    # .PMMSG
    #
    # FORMAT FINAL:
    #   .pmmsg <pesan>
    #   .pmmsg status
    #   .pmmsg reset
    #
    # BUKAN:
    #   .pmmsg set <pesan>
    # ---------------------------------------------------------
    @client.on_message(dynamic_command("pmmsg") & filters.me, group=-150)
    async def cmd_pmmsg(client, message):
        owner_id = await _account_id(client)
        args = _command_args(message)

        if not args:
            current = str(
                get_setting(
                    owner_id,
                    "pm_rejection_message",
                    DEFAULT_PM_MESSAGE,
                )
                or DEFAULT_PM_MESSAGE
            )

            await send_ui(
                client,
                message.chat.id,
                f"📩 PMMSG saat ini:\n{current}\n\n"
                "Gunakan `.pmmsg <pesan>`",
            )
            raise StopPropagation

        first = args[0].casefold()

        if first == "status":
            current = str(
                get_setting(
                    owner_id,
                    "pm_rejection_message",
                    DEFAULT_PM_MESSAGE,
                )
                or DEFAULT_PM_MESSAGE
            )

            await send_ui(
                client,
                message.chat.id,
                f"📩 PMMSG saat ini:\n{current}",
            )
            raise StopPropagation

        if first == "reset" and len(args) == 1:
            set_setting(
                owner_id,
                "pm_rejection_message",
                DEFAULT_PM_MESSAGE,
            )

            await send_ui(
                client,
                message.chat.id,
                "♻️ PMMSG berhasil direset.\n"
                "Pesan kembali ke default.",
            )
            raise StopPropagation

        # Semua input lainnya dianggap sebagai pesan PMMSG.
        payload = " ".join(args).strip()

        set_setting(
            owner_id,
            "pm_rejection_message",
            payload,
        )

        await send_ui(
            client,
            message.chat.id,
            "✅ PMMSG berhasil diganti.",
        )
        raise StopPropagation

    # ---------------------------------------------------------
    # .TAGREPLY
    # ---------------------------------------------------------
    @client.on_message(dynamic_command("tagreply") & filters.me, group=-150)
    async def cmd_tagreply(client, message):
        owner_id = await _account_id(client)
        args = _command_args(message)

        action = args[0].casefold() if args else ""
        payload = " ".join(args[1:]).strip() if len(args) > 1 else ""

        if action == "on" and len(args) == 1:
            set_setting(owner_id, "tagreply_enabled", 1)

            await send_ui(
                client,
                message.chat.id,
                "✅ Tag Reply diaktifkan.",
            )
            raise StopPropagation

        if action == "off" and len(args) == 1:
            set_setting(owner_id, "tagreply_enabled", 0)

            await send_ui(
                client,
                message.chat.id,
                "✅ Tag Reply dimatikan.",
            )
            raise StopPropagation

        if action == "set":
            if not payload:
                await send_ui(
                    client,
                    message.chat.id,
                    "❌ Gunakan: .tagreply set <pesan>",
                )
                raise StopPropagation

            set_setting(
                owner_id,
                "tagreply_message",
                payload,
            )

            await send_ui(
                client,
                message.chat.id,
                "✅ Pesan Tag Reply berhasil disimpan.",
            )
            raise StopPropagation

        if action == "status" and len(args) == 1:
            enabled = bool(
                get_setting(
                    owner_id,
                    "tagreply_enabled",
                    0,
                )
            )

            current = str(
                get_setting(
                    owner_id,
                    "tagreply_message",
                    DEFAULT_TAGREPLY_MESSAGE,
                )
                or DEFAULT_TAGREPLY_MESSAGE
            )

            status = "ON" if enabled else "OFF"

            await send_ui(
                client,
                message.chat.id,
                f"🏷️ Tag Reply: {status}\n"
                f"💬 Pesan: {current}",
            )
            raise StopPropagation

        if action == "reset" and len(args) == 1:
            set_setting(
                owner_id,
                "tagreply_message",
                DEFAULT_TAGREPLY_MESSAGE,
            )

            await send_ui(
                client,
                message.chat.id,
                "♻️ Tag Reply berhasil direset.",
            )
            raise StopPropagation

        await send_ui(
            client,
            message.chat.id,
            "❌ Gunakan:\n"
            ".tagreply on\n"
            ".tagreply off\n"
            ".tagreply set <pesan>\n"
            ".tagreply status\n"
            ".tagreply reset",
        )

    log.info("[PMControl] PM Control + PMMSG + Tag Reply registered.")
    
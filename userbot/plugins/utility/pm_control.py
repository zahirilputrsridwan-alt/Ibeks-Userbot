"""
IBEKS USERBOT - PM Control dan Tag Reply.

Commands:
  .pm all|contacts|nobody
  .pmmsg set <pesan>
  .pmmsg status
  .pmmsg reset
  .tagreply on|off
  .tagreply set <pesan>
  .tagreply status
  .tagreply reset

Semua konfigurasi disimpan melalui settings SQLite yang sudah digunakan
project. Handler gate hanya menangani PM masuk dan mention di grup, sehingga
command/plugin lain tetap berjalan seperti sebelumnya.
"""

from __future__ import annotations

import time
from collections.abc import Iterable

from pyrogram import StopPropagation, filters
from pyrogram.enums import ChatType, MessageEntityType
from pyrogram.errors import Forbidden, FloodWait, RPCError

from db import ensure_user_settings, get_setting, set_setting
from plugins.utils.ui import send_ui
from utils.filters import dynamic_command
from utils.prefix_manager import get_owner_id, set_owner_id

DEFAULT_PM_MODE = "all"
DEFAULT_PM_MESSAGE = "🚫 PM DITOLAK"
DEFAULT_TAGREPLY_MESSAGE = "Ada apa manggil-manggil saya? 😂"
TAGREPLY_COOLDOWN_SECONDS = 8.0

# Debounce in-memory sengaja dipakai hanya untuk mencegah balasan berulang
# selama proses aktif; konfigurasi tetap berada di SQLite.
_last_tag_replies: dict[tuple[int, int], float] = {}


def _command_args(message) -> list[str]:
    text = (message.text or message.caption or "").strip()
    return text.split(maxsplit=1)[1:] if text else []


def _command_payload(message) -> str:
    args = _command_args(message)
    return args[0].strip() if args else ""


async def _account_id(client) -> int:
    """Ambil ID akun userbot dan pastikan settings akun sudah tersedia."""
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
    """Pertahankan pengecualian Owner dari gate PM tanpa membuat permission baru."""
    sender = getattr(message, "from_user", None)
    sender_id = int(getattr(sender, "id", 0) or 0)
    if not sender_id:
        return False
    if sender_id == owner_id:
        return True
    # Pesan dari akun sendiri biasanya bukan incoming, tetapi pengecualian ini
    # menjaga perilaku bila Telegram mengirim update service yang tidak biasa.
    me = await client.get_me()
    return sender_id == int(me.id)


async def _is_contact(client, user_id: int) -> bool:
    """Cek kontak memakai API Pyrogram dengan dukungan objek User atau Dialog.
    Be robust: get_contacts() bisa mengembalikan User objects atau Dialog-like objects
    yang menyimpan .user.
    """
    try:
        contacts = await client.get_contacts()
    except RPCError:
        # Jika ada error API, anggap bukan kontak (lebih aman)
        return False

    ids = set()
    if isinstance(contacts, Iterable):
        for c in contacts:
            # Pyrogram bisa mengembalikan User, or Dialog (dengan attribute .user)
            uid = 0
            if getattr(c, "id", None) is not None:
                uid = int(getattr(c, "id", 0) or 0)
            elif getattr(c, "user", None) is not None:
                uid = int(getattr(getattr(c, "user"), "id", 0) or 0)
            if uid:
                ids.add(uid)
    return user_id in ids


def _entity_mentions_username(message, username: str) -> bool:
    """Deteksi @username dari entity Telegram, bukan pencarian teks biasa."""
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    username = username.casefold().lstrip("@")

    # parse_entities() menangani offset UTF-16 Telegram dengan aman.
    try:
        parsed = message.parse_entities()
        # parsed: dict(MessageEntity -> str) pada Pyrogram; entity.type bisa berupa Enum atau string
        for entity, value in parsed.items():
            etype = getattr(entity, "type", None)
            # allow both enum and string comparisons
            if (etype == MessageEntityType.MENTION) or (str(etype).lower() == "mention"):
                if str(value).casefold().lstrip("@") == username:
                    return True
    except Exception:
        # Fallback tetap mensyaratkan entity MENTION; hanya untuk kompatibilitas
        # objek Message sederhana pada versi Pyrogram yang berbeda.
        for entity in entities:
            etype = getattr(entity, "type", None)
            if (etype == MessageEntityType.MENTION) or (str(etype).lower() == "mention"):
                offset = int(getattr(entity, "offset", 0) or 0)
                length = int(getattr(entity, "length", 0) or 0)
                value = text[offset : offset + length]
                if value.casefold().lstrip("@") == username:
                    return True
    return False


def _usage(command: str) -> str:
    return f"❌ Gunakan: `{command}`"


def setup(client):
    """Daftarkan command konfigurasi dan dua gate otomatis."""

    @client.on_message(filters.incoming & filters.private, group=-90)
    async def pm_gate(client, message):
        """Tolak PM sesuai mode tanpa pernah memproses pesan outgoing."""
        # Hanya tangani pesan masuk dari user (bukan service/chat/channel)
        if getattr(message.chat, "type", None) != ChatType.PRIVATE:
            return

        owner_id = await _account_id(client)
        mode = str(get_setting(owner_id, "pm_mode", DEFAULT_PM_MODE)).casefold()
        if mode == "all":
            return

        sender = getattr(message, "from_user", None)
        sender_id = int(getattr(sender, "id", 0) or 0)
        # Tidak menanggapi service messages, anonymous atau channel-sent
        if not sender_id or await _is_privileged_sender(client, message, owner_id):
            return

        # jika kontak, biarkan saat mode contacts
        if mode == "contacts":
            try:
                if await _is_contact(client, sender_id):
                    return
            except Exception:
                # jika pengecekan kontak gagal, default: tidak dianggap kontak
                pass

        rejection = str(
            get_setting(owner_id, "pm_rejection_message", DEFAULT_PM_MESSAGE)
            or DEFAULT_PM_MESSAGE
        )

        # Kirim balasan aman, hindari crash bila bot tidak dapat mengirim pesan
        try:
            # Reply di private chat aman; hindari reply loop dengan mengecek is_bot
            if getattr(sender, "is_bot", False):
                # Jangan reply bot
                raise StopPropagation
            await message.reply(rejection)
        except Forbidden:
            # bot dilarang mengirim pesan (di-blocked) — nothing to do
            raise StopPropagation
        except FloodWait:
            # bila ada FloodWait, abaikan agar tidak crash (Pyrogram akan raise)
            raise StopPropagation
        except Exception:
            # jangan crash; biarkan handler lain tetap berjalan
            raise StopPropagation
        # Hentikan propagation supaya handler lain tidak memproses PM yang sama
        raise StopPropagation

    @client.on_message(filters.incoming & filters.group, group=-80)
    async def tagreply_gate(client, message):
        """Balas mention akun hanya di grup/supergroup dan saat fitur aktif."""
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
        if not sender_id or await _is_privileged_sender(client, message, owner_id):
            return

        me = await client.get_me()
        username = getattr(me, "username", None)
        if not username or not _entity_mentions_username(message, username):
            return

        now = time.monotonic()
        key = (int(message.chat.id), sender_id)
        if now - _last_tag_replies.get(key, 0.0) < TAGREPLY_COOLDOWN_SECONDS:
            return
        _last_tag_replies[key] = now

        reply_text = str(
            get_setting(owner_id, "tagreply_message", DEFAULT_TAGREPLY_MESSAGE)
            or DEFAULT_TAGREPLY_MESSAGE
        )
        try:
            if getattr(sender, "is_bot", False):
                return
            await message.reply(reply_text)
        except Forbidden:
            return
        except FloodWait:
            return
        except Exception:
            return

    @client.on_message(dynamic_command("pm") & filters.me)
    async def cmd_pm(client, message):
        owner_id = await _account_id(client)
        mode = _command_payload(message).casefold()
        if mode not in {"all", "contacts", "nobody"}:
            await send_ui(
                client,
                message.chat.id,
                "╭─「 ❌ 𝗣𝗠 」\n│\n"
                f"├ 📝 {_usage('.pm all|contacts|nobody')}\n"
                "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
            )
            return
        set_setting(owner_id, "pm_mode", mode)
        labels = {"all": "Semua orang", "contacts": "Kontak saja", "nobody": "Tidak seorang pun"}
        await send_ui(client, message.chat.id, f"✅ PM Control: {labels[mode]}.")

    @client.on_message(dynamic_command("pmmsg") & filters.me)
    async def cmd_pmmsg(client, message):
        owner_id = await _account_id(client)
        args = _command_args(message)
        action = args[0].casefold() if args else ""
        payload = args[1].strip() if len(args) > 1 else ""

        if action == "set" and payload:
            set_setting(owner_id, "pm_rejection_message", payload)
            await send_ui(client, message.chat.id, "✅ Pesan penolakan PM berhasil disimpan.")
        elif action == "status":
            current = get_setting(owner_id, "pm_rejection_message", DEFAULT_PM_MESSAGE)
            await send_ui(client, message.chat.id, f"📩 Pesan penolakan PM saat ini:\n{current}")
        elif action == "reset":
            set_setting(owner_id, "pm_rejection_message", DEFAULT_PM_MESSAGE)
            await send_ui(client, message.chat.id, "✅ Pesan penolakan PM dikembalikan ke default.")
        else:
            await send_ui(
                client,
                message.chat.id,
                "❌ Gunakan: `.pmmsg set <pesan>`, `.pmmsg status`, atau `.pmmsg reset`",
            )

    @client.on_message(dynamic_command("tagreply") & filters.me)
    async def cmd_tagreply(client, message):
        owner_id = await _account_id(client)
        args = _command_args(message)
        action = args[0].casefold() if args else ""
        payload = args[1].strip() if len(args) > 1 else ""

        if action == "on":
            set_setting(owner_id, "tagreply_enabled", 1)
            await send_ui(client, message.chat.id, "✅ Tag Reply diaktifkan.")
        elif action == "off":
            set_setting(owner_id, "tagreply_enabled", 0)
            await send_ui(client, message.chat.id, "✅ Tag Reply dimatikan.")
        elif action == "set" and payload:
            set_setting(owner_id, "tagreply_message", payload)
            await send_ui(client, message.chat.id, "✅ Pesan Tag Reply berhasil disimpan.")
        elif action == "status":
            enabled = bool(get_setting(owner_id, "tagreply_enabled", 0))
            current = get_setting(owner_id, "tagreply_message", DEFAULT_TAGREPLY_MESSAGE)
            status = "ON" if enabled else "OFF"
            await send_ui(
                client,
                message.chat.id,
                f"🏷️ Tag Reply: {status}\n💬 Pesan: {current}",
            )
        elif action == "reset":
            set_setting(owner_id, "tagreply_message", DEFAULT_TAGREPLY_MESSAGE)
            await send_ui(client, message.chat.id, "✅ Pesan Tag Reply dikembalikan ke default.")
        else:
            await send_ui(
                client,
                message.chat.id,
                "❌ Gunakan: `.tagreply on|off|set <pesan>|status|reset`",
            )

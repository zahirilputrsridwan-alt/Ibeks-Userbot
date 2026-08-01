"""
IBEKS USERBOT - Plugin: Broadcast
Commands:
  .gcast <pesan> / .gcast (reply)
  .ucast <pesan> / .ucast (reply)
  .addbl
  .delbl
  .listbl
"""

import asyncio
import time

from pyrogram import filters

from config import AUTO_DELETE_CMD
from db import add_blacklist, del_blacklist, is_blacklisted, list_blacklist
from utils.autodelete import auto_delete
from utils.formatter import format_status
from utils.filters import dynamic_command
from utils.broadcast import broadcast_gcast, broadcast_ucast, format_broadcast_result
from plugins.utils.ui import send_ui


_RECENT_COMMANDS: dict[tuple[int, str], float] = {}
_COMMAND_DEDUPE_SECONDS = 30.0
_ACTIVE_BROADCASTS: set[int] = set()


def _is_duplicate_command(message) -> bool:
    """Abaikan update Telegram yang sama bila diterima ulang."""
    text = (message.text or message.caption or "").strip()
    reply_id = getattr(message.reply_to_message, "id", 0) or 0
    key = (int(message.chat.id), f"{reply_id}:{text}")
    now = time.monotonic()
    expired = [item for item, seen_at in _RECENT_COMMANDS.items()
               if now - seen_at > _COMMAND_DEDUPE_SECONDS]
    for item in expired:
        _RECENT_COMMANDS.pop(item, None)
    if key in _RECENT_COMMANDS:
        return True
    _RECENT_COMMANDS[key] = now
    return False


def setup(client):
    """Daftarkan handler broadcast pada instance client."""

    @client.on_message(dynamic_command("gcast") & filters.me)
    async def cmd_gcast(client, message):
        """Handler command .gcast"""
        if _is_duplicate_command(message):
            return
        chat_id = message.chat.id
        if chat_id in _ACTIVE_BROADCASTS:
            return
        _ACTIVE_BROADCASTS.add(chat_id)
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        reply = message.reply_to_message

        # Ambil konten: reply jika ada, atau teks setelah command
        text = None
        try:
            if reply:
                source = reply
            else:
                parts = (message.text or message.caption or "").split(maxsplit=1)
                if len(parts) < 2:
                    await send_ui(
                        client,
                        chat_id,
                        format_status(False, "Gunakan `.gcast <pesan>` atau reply pesan."),
                        expandable=True,
                    )
                    return
                text = parts[1]
                source = None

            await send_ui(client, chat_id, "🔄 GCAST sedang berjalan...", expandable=True)
            result = await broadcast_gcast(client, text=text, source_message=source)
            await send_ui(client, chat_id, format_broadcast_result("gcast", result), expandable=True)
        finally:
            _ACTIVE_BROADCASTS.discard(chat_id)

    @client.on_message(dynamic_command("ucast") & filters.me)
    async def cmd_ucast(client, message):
        """Handler command .ucast"""
        if _is_duplicate_command(message):
            return
        chat_id = message.chat.id
        if chat_id in _ACTIVE_BROADCASTS:
            return
        _ACTIVE_BROADCASTS.add(chat_id)
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        reply = message.reply_to_message

        text = None
        try:
            if reply:
                source = reply
            else:
                parts = (message.text or message.caption or "").split(maxsplit=1)
                if len(parts) < 2:
                    await send_ui(
                        client,
                        chat_id,
                        format_status(False, "Gunakan `.ucast <pesan>` atau reply pesan."),
                        expandable=True,
                    )
                    return
                text = parts[1]
                source = None

            await send_ui(client, chat_id, "🔄 UCAST sedang berjalan...", expandable=True)
            result = await broadcast_ucast(client, text=text, source_message=source)
            await send_ui(client, chat_id, format_broadcast_result("ucast", result), expandable=True)
        finally:
            _ACTIVE_BROADCASTS.discard(chat_id)

    @client.on_message(dynamic_command("addbl") & filters.me)
    async def cmd_addbl(client, message):
        """Handler command .addbl"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        chat_title = message.chat.title or message.chat.first_name or "Unknown"

        if is_blacklisted(chat_id):
            await send_ui(client, chat_id, format_status(False, "Chat sudah ada di Blacklist."), expandable=True)
            return

        add_blacklist(chat_id, chat_title)
        await send_ui(client, chat_id, format_status(True, "Grup berhasil ditambahkan ke Blacklist."), expandable=True)

    @client.on_message(dynamic_command("delbl") & filters.me)
    async def cmd_delbl(client, message):
        """Handler command .delbl"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        if del_blacklist(chat_id):
            await send_ui(client, chat_id, format_status(True, "Grup berhasil dihapus dari Blacklist."), expandable=True)
        else:
            await send_ui(client, chat_id, format_status(False, "Chat tidak ditemukan di Blacklist."), expandable=True)

    @client.on_message(dynamic_command("listbl") & filters.me)
    async def cmd_listbl(client, message):
        """Handler command .listbl"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        items = list_blacklist()
        if not items:
            await send_ui(client, chat_id, "Tidak ada blacklist.", expandable=True)
            return

        lines = ["📋 BLACKLIST", ""]
        for idx, item in enumerate(items, start=1):
            lines.append(f"{idx}.")
            lines.append(item["chat_title"] or "Unknown")
            lines.append(f"`{item['chat_id']}`")
            lines.append("")
        await send_ui(client, chat_id, "\n".join(lines), expandable=True)

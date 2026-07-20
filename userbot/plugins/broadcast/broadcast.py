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

from pyrogram import filters

from config import AUTO_DELETE_CMD
from db import add_blacklist, del_blacklist, is_blacklisted, list_blacklist
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.formatter import format_status
from utils.broadcast import broadcast_gcast, broadcast_ucast, format_broadcast_result


def setup(client):
    """Daftarkan handler broadcast pada instance client."""

    @client.on_message(dynamic_command("gcast") & filters.me)
    async def cmd_gcast(client, message):
        """Handler command .gcast"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        reply = message.reply_to_message

        # Ambil konten: reply jika ada, atau teks setelah command
        text = None
        if reply:
            source = reply
        else:
            parts = (message.text or message.caption or "").split(maxsplit=1)
            if len(parts) < 2:
                await client.send_message(
                    chat_id,
                    format_status(False, "Gunakan `.gcast <pesan>` atau reply pesan."),
                )
                return
            text = parts[1]
            source = None

        await client.send_message(chat_id, "🔄 GCAST sedang berjalan...")
        result = await broadcast_gcast(client, text=text, source_message=source)
        await client.send_message(chat_id, format_broadcast_result("gcast", result))

    @client.on_message(dynamic_command("ucast") & filters.me)
    async def cmd_ucast(client, message):
        """Handler command .ucast"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        reply = message.reply_to_message

        text = None
        if reply:
            source = reply
        else:
            parts = (message.text or message.caption or "").split(maxsplit=1)
            if len(parts) < 2:
                await client.send_message(
                    chat_id,
                    format_status(False, "Gunakan `.ucast <pesan>` atau reply pesan."),
                )
                return
            text = parts[1]
            source = None

        await client.send_message(chat_id, "🔄 UCAST sedang berjalan...")
        result = await broadcast_ucast(client, text=text, source_message=source)
        await client.send_message(chat_id, format_broadcast_result("ucast", result))

    @client.on_message(dynamic_command("addbl") & filters.me)
    async def cmd_addbl(client, message):
        """Handler command .addbl"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        chat_title = message.chat.title or message.chat.first_name or "Unknown"

        if is_blacklisted(chat_id):
            await client.send_message(
                chat_id,
                format_status(False, "Chat sudah ada di Blacklist."),
            )
            return

        add_blacklist(chat_id, chat_title)
        await client.send_message(
            chat_id,
            format_status(True, "Grup berhasil ditambahkan ke Blacklist."),
        )

    @client.on_message(dynamic_command("delbl") & filters.me)
    async def cmd_delbl(client, message):
        """Handler command .delbl"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        if del_blacklist(chat_id):
            await client.send_message(
                chat_id,
                format_status(True, "Grup berhasil dihapus dari Blacklist."),
            )
        else:
            await client.send_message(
                chat_id,
                format_status(False, "Chat tidak ditemukan di Blacklist."),
            )

    @client.on_message(dynamic_command("listbl") & filters.me)
    async def cmd_listbl(client, message):
        """Handler command .listbl"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        items = list_blacklist()
        if not items:
            await client.send_message(chat_id, "Tidak ada blacklist.")
            return

        lines = ["📋 BLACKLIST", ""]
        for idx, item in enumerate(items, start=1):
            lines.append(f"{idx}.")
            lines.append(item["chat_title"] or "Unknown")
            lines.append(f"`{item['chat_id']}`")
            lines.append("")
        lines.append("⨱ IBEKS UBOT ⨱")

        await client.send_message(chat_id, "\n".join(lines))

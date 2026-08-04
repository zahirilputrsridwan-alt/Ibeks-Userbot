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
from utils.broadcast import broadcast_gcast, broadcast_ucast, format_broadcast_result
from plugins.utils.ui import send_ui

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
                await send_ui(
                    client,
                    chat_id,
                    (
                        "╭─「 ❌ 𝗚𝗖𝗔𝗦𝗧 」\n│\n"
                        "├ 📝 𝗣𝗲𝘀𝗮𝗻\n│  ╰➤ Gunakan `.gcast <pesan>` atau reply pesan.\n"
                        "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
                    ),
                )
                return
            text = parts[1]
            source = None

        await send_ui(
            client,
            chat_id,
            "╭─「 🔄 𝗚𝗖𝗔𝗦𝗧 」\n│\n"
            "├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ Sedang berjalan...\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
        )
        result = await broadcast_gcast(client, text=text, source_message=source)
        await send_ui(client, chat_id, format_broadcast_result("gcast", result), expandable=True)

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
                await send_ui(
                    client,
                    chat_id,
                    (
                        "╭─「 ❌ 𝗨𝗖𝗔𝗦𝗧 」\n│\n"
                        "├ 📝 𝗣𝗲𝘀𝗮𝗻\n│  ╰➤ Gunakan `.ucast <pesan>` atau reply pesan.\n"
                        "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
                    ),
                )
                return
            text = parts[1]
            source = None

        await send_ui(
            client,
            chat_id,
            "╭─「 🔄 𝗨𝗖𝗔𝗦𝗧 」\n│\n"
            "├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ Sedang berjalan...\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
        )
        result = await broadcast_ucast(client, text=text, source_message=source)
        await send_ui(client, chat_id, format_broadcast_result("ucast", result), expandable=True)

    @client.on_message(dynamic_command("addbl") & filters.me)
    async def cmd_addbl(client, message):
        """Handler command .addbl"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        chat_title = message.chat.title or message.chat.first_name or "Unknown"

        if is_blacklisted(chat_id):
            await send_ui(
                client,
                chat_id,
                "╭─「 ❌ 𝗔𝗗𝗗𝗕𝗟 」\n│\n"
                "├ 💬 𝗖𝗵𝗮𝘁\n│  ╰➤ Chat sudah ada di Blacklist.\n"
                "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
            )
            return

        add_blacklist(chat_id, chat_title)
        await send_ui(
            client,
            chat_id,
            f"╭─「 ✅ 𝗔𝗗𝗗𝗕𝗟 」\n│\n"
            f"├ 💬 𝗖𝗵𝗮𝘁\n│  ╰➤ {chat_title}\n"
            "├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ Berhasil ditambahkan ke Blacklist.\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
        )

    @client.on_message(dynamic_command("delbl") & filters.me)
    async def cmd_delbl(client, message):
        """Handler command .delbl"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        if del_blacklist(chat_id):
            await send_ui(
                client,
                chat_id,
                "╭─「 ✅ 𝗗𝗘𝗟𝗕𝗟 」\n│\n"
                f"├ 🆔 𝗖𝗵𝗮𝘁 𝗜𝗗\n│  ╰➤ `{chat_id}`\n"
                "├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ Berhasil dihapus dari Blacklist.\n"
                "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
            )
        else:
            await send_ui(
                client,
                chat_id,
                "╭─「 ❌ 𝗗𝗘𝗟𝗕𝗟 」\n│\n"
                f"├ 🆔 𝗖𝗵𝗮𝘁 𝗜𝗗\n│  ╰➤ `{chat_id}`\n"
                "├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ Chat tidak ditemukan di Blacklist.\n"
                "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
            )

    @client.on_message(dynamic_command("listbl") & filters.me)
    async def cmd_listbl(client, message):
        """Handler command .listbl"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        items = list_blacklist()
        if not items:
            await send_ui(
                client,
                chat_id,
                "╭─「 📋 𝗕𝗟𝗔𝗖𝗞𝗟𝗜𝗦𝗧 」\n│\n"
                "├ 📋 𝗗𝗮𝗳𝘁𝗮𝗿\n│  ╰➤ Tidak ada blacklist.\n"
                "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
            )
            return

        lines = ["╭─「 📋 𝗕𝗟𝗔𝗖𝗞𝗟𝗜𝗦𝗧 」", "│"]
        for idx, item in enumerate(items, start=1):
            lines.extend(
                [
                    f"├ {idx}. 𝗖𝗵𝗮𝘁\n│  ╰➤ {item['chat_title'] or 'Unknown'}",
                    f"├ 🆔 𝗖𝗵𝗮𝘁 𝗜𝗗\n│  ╰➤ `{item['chat_id']}`",
                ]
            )
        lines.extend(["│", "╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"])
        await send_ui(client, chat_id, "\n".join(lines), expandable=True)

"""
IBEKS USERBOT - Plugin: Fun
Commands:
  .ctampan       - Cek ketampanan akun sendiri atau yang direply
  .ccantik       - Cek kecantikan akun sendiri atau yang direply

Nilai deterministik berdasarkan User ID + minggu ISO saat ini.
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.fun_generator import generate_ctampan, generate_ccantik
from plugins.utils.ui import send_ui


def setup(client):
    """Daftarkan handler fun commands."""

    @client.on_message(dynamic_command("ctampan") & filters.me)
    async def cmd_ctampan(client, message):
        """Handler command .ctampan"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        target_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user

        if not target_user:
            await send_ui(
                client,
                chat_id,
                "╭─「 ❌ 𝗖𝗘𝗞 𝗧𝗔𝗠𝗣𝗔𝗡 」\n│\n"
                "├ 👤 𝗧𝗮𝗿𝗴𝗲𝘁\n│  ╰➤ Tidak ditemukan.\n"
                "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
            )
            return

        name, user_id, progress, aura, outfit, plus, tier = generate_ctampan(target_user)

        text = (
            "╭─「 ✨ 𝗖𝗘𝗞 𝗧𝗔𝗠𝗣𝗔𝗡 」\n│\n"
            f"├ 👤 𝗧𝗮𝗿𝗴𝗲𝘁\n│  ╰➤ `{name}`\n"
            f"├ 🆔 𝗜𝗗\n│  ╰➤ `{user_id}`\n"
            f"├ 📊 𝗞𝗲𝘁𝗮𝗺𝗽𝗮𝗻𝗮𝗻\n│  ╰➤ {progress}\n"
            f"├ 😎 𝗔𝘂𝗿𝗮\n│  ╰➤ {aura}\n"
            f"├ 👕 𝗢𝘂𝘁𝗳𝗶𝘁\n│  ╰➤ {outfit}\n"
            f"├ ⭐ 𝗣𝗹𝘂𝘀\n│  ╰➤ {plus}\n"
            f"├ 👑 𝗧𝗶𝗲𝗿\n│  ╰➤ {tier}\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
        )
        await send_ui(client, chat_id, text, expandable=True)

    @client.on_message(dynamic_command("ccantik") & filters.me)
    async def cmd_ccantik(client, message):
        """Handler command .ccantik"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        target_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user

        if not target_user:
            await send_ui(
                client,
                chat_id,
                "╭─「 ❌ 𝗖𝗘𝗞 𝗖𝗔𝗡𝗧𝗜𝗞 」\n│\n"
                "├ 👤 𝗧𝗮𝗿𝗴𝗲𝘁\n│  ╰➤ Tidak ditemukan.\n"
                "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
            )
            return

        name, user_id, progress, aura, outfit, plus, tier = generate_ccantik(target_user)

        text = (
            "╭─「 ✨ 𝗖𝗘𝗞 𝗖𝗔𝗡𝗧𝗜𝗞 」\n│\n"
            f"├ 👤 𝗧𝗮𝗿𝗴𝗲𝘁\n│  ╰➤ `{name}`\n"
            f"├ 🆔 𝗜𝗗\n│  ╰➤ `{user_id}`\n"
            f"├ 📊 𝗞𝗲𝗰𝗮𝗻𝘁𝗶𝗸𝗮𝗻\n│  ╰➤ {progress}\n"
            f"├ 💖 𝗔𝘂𝗿𝗮\n│  ╰➤ {aura}\n"
            f"├ 👗 𝗢𝘂𝘁𝗳𝗶𝘁\n│  ╰➤ {outfit}\n"
            f"├ ⭐ 𝗣𝗹𝘂𝘀\n│  ╰➤ {plus}\n"
            f"├ 👑 𝗧𝗶𝗲𝗿\n│  ╰➤ {tier}\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
        )
        await send_ui(client, chat_id, text, expandable=True)

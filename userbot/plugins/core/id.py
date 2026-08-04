"""
IBEKS USERBOT - Plugin: id
Command: .id
Menampilkan kartu identitas futuristik IBEKS USERBOT untuk user target
atau akun sendiri. Hasilnya berupa gambar PNG dengan foto profil,
informasi user, HUD lines, barcode, dan QR.
"""

import asyncio

from pyrogram import filters
from pyrogram.types import InputMediaDocument

from config import AUTO_DELETE_CMD
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from utils.id_card_generator import generate_id_card
from plugins.utils.ui import send_ui


def setup(client):
    """Daftarkan handler .id pada instance client."""

    @client.on_message(dynamic_command("id") & filters.me)
    async def cmd_id(client, message):
        """Handler command .id"""
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))

        chat_id = message.chat.id
        target = message.reply_to_message.from_user if message.reply_to_message else message.from_user

        try:
            card_buffer = await generate_id_card(client, target)
            card_buffer.name = f"ibeks_id_{target.id}.png"
            await client.send_document(
                chat_id=chat_id,
                document=card_buffer,
                caption=f"🆔 ID Card untuk {target.first_name or 'User'}",
                force_document=True,
            )
        except Exception as exc:
            import logging
            logging.exception("[ID] Gagal generate ID card: %s", exc)
            await send_ui(
                client,
                chat_id,
                f"Gagal generate ID card: {exc}",
                title="ID CARD",
                emoji="❌",
            )

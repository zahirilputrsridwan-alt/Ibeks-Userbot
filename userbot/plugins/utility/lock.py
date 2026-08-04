"""IBEKS USERBOT - Chat Lock.

Commands:
  .lock   - Kunci chat saat ini.
  .unlock - Buka chat yang sedang dikunci.
"""

from pyrogram import StopPropagation, filters

from config import OWNER_ID
from db import is_chat_locked, set_chat_lock
from plugins.utils.ui import send_ui
from utils.filters import dynamic_command
from utils.prefix_manager import get_prefix


def _command_name(message) -> str:
    text = (message.text or message.caption or "").strip()
    return text.split(maxsplit=1)[0].casefold()


def _is_command(message) -> bool:
    return bool(
        (message.text or message.caption or "").strip().startswith(get_prefix())
    )


async def _is_owner(client) -> bool:
    """Pastikan hanya akun Owner terkonfigurasi yang mengubah lock."""
    if not OWNER_ID:
        return False
    me = await client.get_me()
    return me.id == OWNER_ID


def setup(client):
    """Daftarkan gate global dan command lock/unlock."""

    @client.on_message(filters.me & filters.text, group=-100)
    async def locked_chat_gate(client, message):
        if not _is_command(message):
            return

        chat_id = message.chat.id
        if not is_chat_locked(chat_id):
            return

        command = _command_name(message)
        if command == f"{get_prefix()}unlock":
            return

        await send_ui(client, chat_id, "❌ Chat ini sedang dikunci.")
        raise StopPropagation

    @client.on_message(dynamic_command("lock") & filters.me)
    async def cmd_lock(client, message):
        chat_id = message.chat.id
        if not await _is_owner(client):
            await send_ui(client, chat_id, "❌ Hanya Owner yang dapat menggunakan perintah ini.")
            return

        set_chat_lock(chat_id, True)
        await send_ui(client, chat_id, "🔒 Chat ini berhasil dikunci.")

    @client.on_message(dynamic_command("unlock") & filters.me)
    async def cmd_unlock(client, message):
        chat_id = message.chat.id
        if not await _is_owner(client):
            await send_ui(client, chat_id, "❌ Hanya Owner yang dapat menggunakan perintah ini.")
            return

        if not is_chat_locked(chat_id):
            await send_ui(client, chat_id, "ℹ️ Chat ini tidak sedang dikunci.")
            return

        set_chat_lock(chat_id, False)
        await send_ui(client, chat_id, "🔓 Chat ini berhasil dibuka kembali.")
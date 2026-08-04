"""
IBEKS USERBOT - Broadcast Utilities
Helper untuk operasi broadcast (gcast/u cast) dengan penanganan FloodWait,
blacklist, dan delay antar pengiriman.
"""

import asyncio
import uuid
from typing import Optional

from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from db import is_blacklisted
from utils.logger import log


BROADCAST_DELAY: float = 1.0  # Jeda antar pengiriman (detik)


def _generate_task_id() -> str:
    """Generate task ID singkat untuk broadcast."""
    return uuid.uuid4().hex[:8].upper()


async def _send_message_to_chat(
    client: Client,
    chat_id: int,
    text: Optional[str] = None,
    source_message: Optional[Message] = None,
) -> bool:
    """
    Kirim pesan ke satu chat. Gunakan copy jika source_message tersedia,
    atau send_message jika hanya text.
    Return True jika berhasil, False jika gagal.
    """
    try:
        if source_message is not None:
            await source_message.copy(chat_id)
        else:
            await client.send_message(chat_id, text or "")
        return True
    except FloodWait as exc:
        # Tunggu sesuai permintaan Telegram lalu coba sekali lagi
        wait = exc.value
        log.warning(f"[Broadcast] FloodWait {wait}s untuk chat {chat_id}")
        await asyncio.sleep(wait)
        try:
            if source_message is not None:
                await source_message.copy(chat_id)
            else:
                await client.send_message(chat_id, text or "")
            return True
        except Exception as exc2:
            log.warning(f"[Broadcast] Gagal kirim ulang ke chat {chat_id}: {exc2}")
            return False
    except Exception as exc:
        log.warning(f"[Broadcast] Gagal kirim ke chat {chat_id}: {exc}")
        return False


async def broadcast_gcast(
    client: Client,
    text: Optional[str] = None,
    source_message: Optional[Message] = None,
) -> dict:
    """
    Broadcast pesan ke semua grup/channel yang diikuti userbot.
    Return dict {'success', 'failed', 'total', 'task_id'}.
    """
    task_id = _generate_task_id()
    success = 0
    failed = 0

    async for dialog in client.get_dialogs():
        chat = dialog.chat
        if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL):
            continue
        if is_blacklisted(chat.id):
            continue

        if await _send_message_to_chat(client, chat.id, text, source_message):
            success += 1
        else:
            failed += 1

        await asyncio.sleep(BROADCAST_DELAY)

    total = success + failed
    return {
        "success": success,
        "failed": failed,
        "total": total,
        "task_id": task_id,
    }


async def broadcast_ucast(
    client: Client,
    text: Optional[str] = None,
    source_message: Optional[Message] = None,
) -> dict:
    """
    Broadcast pesan ke semua chat pribadi (private).
    Return dict {'success', 'failed', 'total', 'task_id'}.
    """
    task_id = _generate_task_id()
    success = 0
    failed = 0

    async for dialog in client.get_dialogs():
        chat = dialog.chat
        if chat.type != ChatType.PRIVATE:
            continue
        if is_blacklisted(chat.id):
            continue

        if await _send_message_to_chat(client, chat.id, text, source_message):
            success += 1
        else:
            failed += 1

        await asyncio.sleep(BROADCAST_DELAY)

    total = success + failed
    return {
        "success": success,
        "failed": failed,
        "total": total,
        "task_id": task_id,
    }


def format_broadcast_result(broadcast_type: str, result: dict) -> str:
    """Format hasil broadcast dengan field hasil yang nyata."""
    label = broadcast_type.upper()
    return (
        f"╭─「 ✅ 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 {label} 」\n│\n"
        f"├ ✅ 𝗦𝘂𝗰𝗰𝗲𝘀𝘀\n│  ╰➤ {result['success']}\n"
        f"├ ❌ 𝗙𝗮𝗶𝗹𝗲𝗱\n│  ╰➤ {result['failed']}\n"
        f"├ 📊 𝗧𝗼𝘁𝗮𝗹\n│  ╰➤ {result['total']}\n"
        f"├ 🤖 𝗧𝘆𝗽𝗲\n│  ╰➤ {label}\n"
        f"├ 📎 𝗧𝗮𝘀𝗸 𝗜𝗗\n│  ╰➤ {result['task_id']}\n"
        "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
    )

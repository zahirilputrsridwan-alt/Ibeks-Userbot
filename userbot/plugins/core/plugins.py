"""
IBEKS USERBOT - Plugin Manager
Command: .plugins
Menampilkan jumlah plugin aktif berdasarkan kategori folder.
"""

import asyncio

from pyrogram import filters

from config import AUTO_DELETE_CMD, BOT_NAME
from loader import get_plugin_stats, plugin_category
from utils.autodelete import auto_delete
from utils.filters import dynamic_command
from plugins.utils.ui import send_ui


def _category_counts(plugin_stats: dict) -> dict[str, int]:
    counts = {
        "Core": 0,
        "Broadcast": 0,
        "Voice": 0,
        "Fun": 0,
        "AI": 0,
        "Permission": 0,
    }
    for module in plugin_stats["loaded"]:
        category = plugin_category(module)
        counts[category] = counts.get(category, 0) + 1
    return counts


def _format_plugin_status() -> str:
    stats = get_plugin_stats()
    counts = _category_counts(stats)
    lines = [
        f"╭─「 📦 𝗣𝗟𝗨𝗚𝗜𝗡 𝗦𝗧𝗔𝗧𝗨𝗦 」",
        "│",
        f"├ 🤖 𝗕𝗼𝘁\n│  ╰➤ {BOT_NAME}",
        f"├ 📊 𝗧𝗼𝘁𝗮𝗹 𝗣𝗹𝘂𝗴𝗶𝗻\n│  ╰➤ {len(stats['loaded'])}",
    ]
    for category, count in counts.items():
        lines.append(f"├ 📂 𝗖𝗮𝘁𝗲𝗴𝗼𝗿𝘆 {category}\n│  ╰➤ {count}")
    lines.extend(
        [
            "├ 📦 𝗩𝗲𝗿𝘀𝗶\n│  ╰➤ 1.0",
            "│",
            "╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
        ]
    )
    return "\n".join(lines)


def setup(client):
    """Daftarkan handler .plugins."""

    @client.on_message(dynamic_command("plugins") & filters.me)
    async def cmd_plugins(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        try:
            await send_ui(client, message.chat.id, _format_plugin_status(), expandable=True)
        except Exception:
            from utils.logger import log

            log.exception("[PluginManager] Gagal mengirim status plugin.")
"""
IBEKS USERBOT - Dynamic Filters
Filter Pyrogram dinamis yang membaca prefix dari database.
"""

from pyrogram import filters

from utils.prefix_manager import get_prefix


def dynamic_command(*commands):
    """
    Filter command yang membaca prefix dari database secara dinamis.

    Usage:
        @client.on_message(dynamic_command("ping") & filters.me)
        async def cmd_ping(client, message): ...
    """
    async def filter_func(filter_obj, client, message):
        if not message or (not message.text and not message.caption):
            return False
        text = (message.text or message.caption).strip()
        prefix = get_prefix()
        for cmd in filter_obj.commands:
            full = f"{prefix}{cmd}"
            if text == full or text.startswith(full + " "):
                return True
        return False
    return filters.create(filter_func, "DynamicCommandFilter", commands=commands)

"""
IBEKS USERBOT - Formatter Utilities
Utilitas formatting untuk menampilkan informasi user, chat, dan data lainnya
ke dalam pesan Telegram dengan format yang rapi.
"""

from typing import Optional

from pyrogram.types import User


def escape_md(text: Optional[str]) -> str:
    """Escape karakter Markdown umum agar tidak terbaca sebagai format."""
    if not text:
        return ""
    chars = ["_", "*", "[", "]", "(", ")", "~", "`", "\\", ">", "#", "+", "-", "=", "|", "{", "}"]
    for ch in chars:
        text = text.replace(ch, f"\\{ch}")
    return text


def mention(user: User) -> str:
    """Buat mention dari objek User."""
    if user.username:
        return f"@{user.username}"
    name = user.first_name or "Unknown"
    return f"[{escape_md(name)}](tg://user?id={user.id})"


def format_user_info(user: User, chat_id: Optional[int] = None) -> str:
    """Format informasi user untuk command .id"""
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Unknown"
    username = f"@{user.username}" if user.username else "Tidak ada"
    status = "Bot" if user.is_bot else "User"
    lines = [
        "╭━━━━━━━━━━━━━━━━━━━━━━╮",
        "        ℹ️ INFO USER",
        "╰━━━━━━━━━━━━━━━━━━━━━━╯",
        "",
        f"👤 **Nama**      : `{escape_md(name)}`",
        f"🔗 **Username**  : `{escape_md(username)}`",
        f"🆔 **User ID**   : `{user.id}`",
        f"🤖 **Status**    : `{status}`",
    ]
    if chat_id is not None:
        lines.append(f"💬 **Chat ID**   : `{chat_id}`")
    lines.extend(["", "╰━━━━━━━━━━━━━━━━━━━━━━╯"])
    return "\n".join(lines)


def format_me_info(user: User) -> str:
    """Format informasi akun sendiri untuk command .me"""
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Unknown"
    username = f"@{user.username}" if user.username else "Tidak ada"
    premium = "Ya" if getattr(user, "is_premium", False) else "Tidak"
    dc_id = getattr(user, "dc_id", None)
    dc_info = f"`{dc_id}`" if dc_id else "Tidak tersedia"

    return (
        "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "        👤 INFO AKUN\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━╯\n"
        "\n"
        f"👤 **Nama**      : `{escape_md(name)}`\n"
        f"🔗 **Username**  : `{escape_md(username)}`\n"
        f"🆔 **User ID**   : `{user.id}`\n"
        f"⭐ **Premium**   : `{premium}`\n"
        f"🌐 **DC ID**     : `{dc_info}`\n"
        "\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━╯"
    )


def format_status(success: bool, text: str) -> str:
    """Format pesan status dengan emoji centang/silang."""
    emoji = "✅" if success else "❌"
    return f"{emoji} {text}"

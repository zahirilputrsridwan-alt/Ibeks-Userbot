"""Formatter teks Manager Bot."""

from __future__ import annotations

from datetime import datetime


def display_username(username: str | None) -> str:
    return f"@{username}" if username else "Tidak ada"


def display_date(value: str | None) -> str:
    if not value:
        return "Tidak diketahui"
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone().strftime("%d-%m-%Y %H:%M")
    except ValueError:
        return value


def full_name(user) -> str:
    name = " ".join(part for part in [user.first_name, user.last_name] if part)
    return name or user.username or "Pengguna Telegram"


def account_text(user_data: dict) -> str:
    status = user_data.get("status") or "Belum Aktif"
    status_line = "🟢 Aktif" if status == "Aktif" else "🔴 Belum Aktif"
    return (
        "👤 **Akun Saya**\n\n"
        f"• Nama : {user_data.get('full_name') or 'Tidak diketahui'}\n"
        f"• Username : {display_username(user_data.get('username'))}\n"
        f"• Telegram ID : `{user_data.get('telegram_id')}`\n"
        f"• Status : {status_line}\n"
        f"• Tanggal Bergabung : {display_date(user_data.get('created_at'))}"
    )


def welcome_text() -> str:
    return "👋 **Selamat Datang di IBEKS USERBOT**\n\nSilakan pilih menu di bawah."


def guide_text() -> str:
    return (
        "📖 **Panduan IBEKS USERBOT**\n\n"
        "Gunakan menu Manager Bot untuk mengelola akun dan akses layanan "
        "IBEKS USERBOT. Ikuti instruksi pada setiap menu yang tersedia.\n\n"
        "Fitur login dan pengelolaan Userbot akan tersedia pada tahap berikutnya."
    )


def about_text(name: str, version: str, python_version: str, pyrogram_version: str) -> str:
    return (
        "ℹ️ **Tentang**\n\n"
        f"Nama Bot : {name}\n"
        f"Versi : {version}\n"
        f"Python : {python_version}\n"
        f"Pyrogram : {pyrogram_version}"
    )

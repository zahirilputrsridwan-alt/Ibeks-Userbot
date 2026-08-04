"""Formatter teks yang dipakai plugin Manager Bot."""

from __future__ import annotations

from datetime import datetime


def box_text(body: str, title: str, emoji: str = "📦") -> str:
    """Format seluruh output teks Manager dengan UI kartu IBEKS."""
    body = str(body or "").strip()
    if body.startswith("╭─「 ") and body.endswith("⨱"):
        return body
    rows = [f"╭─「 {emoji} 𝗝𝗨𝗗𝗨𝗟 {title} 」", "│"]
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        lines = ["Tidak ada informasi."]
    for line in lines:
        if ":" in line:
            label, value = (part.strip() for part in line.split(":", 1))
        else:
            label, value = "Info", line
        rows.extend((f"├ 🔹 𝗟𝗮𝗯𝗲𝗹 {label}", f"│  ╰➤ {value}", "│"))
    rows.append("╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
    return "\n".join(rows)


def full_name(user) -> str:
    return " ".join(
        part
        for part in [
            getattr(user, "first_name", None),
            getattr(user, "last_name", None),
        ]
        if part
    ) or "Pengguna Telegram"


def display_username(username: str | None) -> str:
    return f"@{username}" if username else "Tidak ada"


def display_date(value: str | None) -> str:
    if not value:
        return "Belum tersedia"
    try:
        return datetime.fromisoformat(value).strftime("%d-%m-%Y %H:%M UTC")
    except ValueError:
        return value


def welcome_text() -> str:
    return box_text(
        "Selamat datang di IBEKS USERBOT.\n"
        "Silakan pilih menu di bawah untuk mulai menggunakan layanan.",
        "MENU UTAMA",
        "👋",
    )


def account_text(user_data: dict) -> str:
    status = user_data.get("status") or "Belum Aktif"
    if status == "Active":
        status_line = "🟢 Active"
    elif status == "Expired":
        status_line = "🔴 Expired"
    elif status == "Pending":
        status_line = "🟡 Pending"
    else:
        status_line = "🔴 Belum Aktif"
    userbot_status = user_data.get("userbot_status") or "Offline"
    userbot_status_line = {
        "Online": "🟢 Online",
        "Starting": "🟡 Starting",
        "Offline": "🔴 Offline",
    }.get(userbot_status, f"🔴 {userbot_status}")
    plan = user_data.get("plan") or "FREE"
    remaining = user_data.get("remaining_days")
    remaining_line = "Lifetime" if remaining == -1 else f"{remaining or 0} hari"
    expired_at = (
        "Lifetime"
        if remaining == -1
        else display_date(user_data.get("expired_at"))
    )
    return box_text(
        (
        f"Nama : {user_data.get('full_name') or 'Tidak diketahui'}\n"
        f"Username : {display_username(user_data.get('username'))}\n"
        f"Telegram ID : {user_data.get('telegram_id')}\n"
        f"Status : {status_line}\n"
        f"Plan : {plan}\n"
        f"Sisa Hari : {remaining_line}\n"
        f"Expired : {expired_at}\n"
        f"Userbot : {userbot_status_line}\n"
        f"Mulai Terakhir : {display_date(user_data.get('last_started'))}\n"
        f"Berhenti Terakhir : {display_date(user_data.get('last_stopped'))}\n"
        f"Tanggal Bergabung : {display_date(user_data.get('created_at'))}"
        ),
        "AKUN SAYA",
        "👤",
    )


def guide_text() -> str:
    return box_text(
        (
        "1. Tekan Minta Akses.\n"
        "2. Masukkan nomor Telegram.\n"
        "3. Verifikasi OTP.\n"
        "4. Userbot aktif."
        ),
        "PANDUAN",
        "📖",
    )


def about_text(
    name: str,
    version: str,
    developer: str,
    python_version: str,
    pyrogram_version: str,
) -> str:
    return box_text(
        (
        f"Nama Bot : {name}\n"
        f"Versi : {version}\n"
        f"Developer : {developer}\n"
        "Library : Pyrogram\n"
        f"Python : {python_version}\n"
        f"Pyrogram : {pyrogram_version}"
        ),
        "TENTANG",
        "ℹ️",
    )
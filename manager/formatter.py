"""Formatter teks yang dipakai plugin Manager Bot."""

from __future__ import annotations

from datetime import datetime


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
    return (
        "╭─「 👋 𝗠𝗘𝗡𝗨 𝗨𝗧𝗔𝗠𝗔 」\n"
        "│\n"
        "├ 👋 𝗦𝗲𝗹𝗮𝗺𝗮𝘁 𝗗𝗮𝘁𝗮𝗻𝗴\n"
        "│  ╰➤ Pilih menu di bawah.\n"
        "│\n"
        "╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
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
    return (
        "╭─「 👤 𝗔𝗞𝗨𝗡 𝗦𝗔𝗬𝗔 」\n"
        "│\n"
        f"├ 👤 𝗡𝗮𝗺𝗮\n│  ╰➤ {user_data.get('full_name') or 'Tidak diketahui'}\n"
        f"├ 🔗 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲\n│  ╰➤ {display_username(user_data.get('username'))}\n"
        f"├ 🆔 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗜𝗗\n│  ╰➤ {user_data.get('telegram_id')}\n"
        f"├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ {status_line}\n"
        f"├ 📦 𝗣𝗹𝗮𝗻\n│  ╰➤ {plan}\n"
        f"├ ⏳ 𝗦𝗶𝘀𝗮 𝗛𝗮𝗿𝗶\n│  ╰➤ {remaining_line}\n"
        f"├ 📅 𝗘𝘅𝗽𝗶𝗿𝗲𝗱\n│  ╰➤ {expired_at}\n"
        f"├ 🤖 𝗨𝘀𝗲𝗿𝗯𝗼𝘁\n│  ╰➤ {userbot_status_line}\n"
        f"├ ▶️ 𝗠𝘂𝗹𝗮𝗶 𝗧𝗲𝗿𝗮𝗸𝗵𝗶𝗿\n│  ╰➤ {display_date(user_data.get('last_started'))}\n"
        f"├ ⏹ 𝗕𝗲𝗿𝗵𝗲𝗻𝘁𝗶 𝗧𝗲𝗿𝗮𝗸𝗵𝗶𝗿\n│  ╰➤ {display_date(user_data.get('last_stopped'))}\n"
        f"├ 🗓 𝗧𝗮𝗻𝗴𝗴𝗮𝗹 𝗕𝗲𝗿𝗴𝗮𝗯𝘂𝗻𝗴\n│  ╰➤ {display_date(user_data.get('created_at'))}\n"
        "│\n"
        "╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
    )


def guide_text() -> str:
    return (
        "╭─「 📖 𝗣𝗔𝗡𝗗𝗨𝗔𝗡 」\n"
        "│\n"
        "├ 1️⃣ 𝗟𝗮𝗻𝗴𝗸𝗮𝗵 𝟭\n│  ╰➤ Tekan Minta Akses.\n"
        "├ 2️⃣ 𝗟𝗮𝗻𝗴𝗸𝗮𝗵 𝟮\n│  ╰➤ Masukkan nomor Telegram.\n"
        "├ 3️⃣ 𝗟𝗮𝗻𝗴𝗸𝗮𝗵 𝟯\n│  ╰➤ Verifikasi OTP.\n"
        "├ 4️⃣ 𝗟𝗮𝗻𝗴𝗸𝗮𝗵 𝟰\n│  ╰➤ Userbot aktif.\n"
        "│\n"
        "╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
    )


def about_text(
    name: str,
    version: str,
    developer: str,
    python_version: str,
    pyrogram_version: str,
) -> str:
    return (
        "╭─「 ℹ️ 𝗧𝗘𝗡𝗧𝗔𝗡𝗚 」\n"
        "│\n"
        f"├ 🤖 𝗡𝗮𝗺𝗮 𝗕𝗼𝘁\n│  ╰➤ {name}\n"
        f"├ 📦 𝗩𝗲𝗿𝘀𝗶\n│  ╰➤ {version}\n"
        f"├ 👨‍💻 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿\n│  ╰➤ {developer}\n"
        "├ 🐍 𝗟𝗶𝗯𝗿𝗮𝗿𝘆\n│  ╰➤ Pyrogram\n"
        f"├ 🐍 𝗣𝘆𝘁𝗵𝗼𝗻\n│  ╰➤ {python_version}\n"
        f"├ ⚙️ 𝗣𝘆𝗿𝗼𝗴𝗿𝗮𝗺\n│  ╰➤ {pyrogram_version}\n"
        "│\n"
        "╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
    )
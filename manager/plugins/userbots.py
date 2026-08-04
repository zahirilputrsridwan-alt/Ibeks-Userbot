"""Kontrol Owner untuk lifecycle Userbot per akun."""

from __future__ import annotations

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import OWNER_ID
from database import list_users
from formatter import display_date, display_username
from logger import log, safe_handler
from runner import get_runner


def _owner(query_or_message) -> bool:
    user = getattr(query_or_message, "from_user", None)
    return bool(OWNER_ID and user and user.id == OWNER_ID)


def _userbots_text(users: list[dict]) -> str:
    if not users:
        return (
            "╭─「 🤖 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 𝗠𝗔𝗡𝗔𝗚𝗘𝗥 」\n│\n"
            "├ 👤 𝗔𝗸𝘂𝗻\n│  ╰➤ Belum ada akun terdaftar.\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
        )
    lines = ["╭─「 🤖 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 𝗠𝗔𝗡𝗔𝗚𝗘𝗥 」", "│"]
    for user in users:
        lines.extend(
            [
                f"├ 👤 𝗡𝗮𝗺𝗮\n│  ╰➤ {user.get('full_name') or 'Tidak diketahui'}",
                f"├ 🆔 𝗜𝗗\n│  ╰➤ `{user['telegram_id']}`",
                f"├ 🔗 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲\n│  ╰➤ {display_username(user.get('username'))}",
                f"├ 🔐 𝗔𝗸𝘀𝗲𝘀\n│  ╰➤ {user.get('status') or 'Belum Aktif'} / "
                f"{user.get('approval_status') or 'pending'}",
                f"├ 🤖 𝗨𝘀𝗲𝗿𝗯𝗼𝘁\n│  ╰➤ {user.get('userbot_status') or 'Offline'}",
                f"├ ▶️ 𝗠𝘂𝗹𝗮𝗶\n│  ╰➤ {display_date(user.get('last_started'))}",
                "",
            ]
        )
    lines.append("╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
    return "\n".join(lines)


def _userbots_keyboard(users: list[dict]) -> InlineKeyboardMarkup | None:
    rows = []
    for user in users:
        telegram_id = int(user["telegram_id"])
        status = user.get("userbot_status") or "Offline"
        if status in {"Online", "Starting"}:
            rows.append(
                [
                    InlineKeyboardButton(
                        f"⏹ Stop {telegram_id}",
                        callback_data=f"runner:stop:{telegram_id}",
                    )
                ]
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        f"▶️ Start {telegram_id}",
                        callback_data=f"runner:start:{telegram_id}",
                    )
                ]
            )
    return InlineKeyboardMarkup(rows) if rows else None


async def _render(message, *, answer: str | None = None) -> None:
    users = list_users()
    await message.edit(
        _userbots_text(users),
        reply_markup=_userbots_keyboard(users),
    )
    if answer:
        await message.reply(
            "╭─「 ℹ️ 𝗛𝗔𝗦𝗜𝗟 𝗔𝗞𝗦𝗜 」\n│\n"
            f"├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ {answer}\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
        )


def setup(client):
    @client.on_message(filters.command("userbots") & filters.private)
    @safe_handler
    async def userbots_command(_client, message):
        if not _owner(message):
            await message.reply(
                "╭─「 ⛔ 𝗔𝗞𝗦𝗘𝗦 」\n│\n"
                "├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ Akses ditolak.\n"
                "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
            )
            return
        users = list_users()
        await message.reply(
            _userbots_text(users),
            reply_markup=_userbots_keyboard(users),
        )

    @client.on_callback_query(filters.regex(r"^runner:(start|stop):\d+$"))
    @safe_handler
    async def runner_callback(_client, query):
        if not _owner(query):
            await query.answer("⛔ Akses ditolak.", show_alert=True)
            return
        parts = query.data.split(":")
        action = parts[1]
        telegram_id = int(parts[2])
        runner = get_runner()
        if runner is None:
            await query.answer("Runner belum aktif.", show_alert=True)
            return
        if action == "start":
            success = runner.start_userbot(telegram_id, reason="Owner manual start")
            text = "▶️ Perintah start dikirim." if success else "❌ User tidak memenuhi syarat akses."
        else:
            success = runner.stop_userbot(
                telegram_id,
                reason="Owner manual stop",
                suppress_restart=True,
            )
            text = "⏹ Userbot dihentikan." if success else "ℹ️ Userbot sudah offline."
        await query.answer(text, show_alert=not success)
        if query.message:
            await query.message.edit(
                _userbots_text(list_users()),
                reply_markup=_userbots_keyboard(list_users()),
            )
        log.info(
            "[Runner] Owner action=%s telegram_id=%s success=%s.",
            action,
            telegram_id,
            success,
        )
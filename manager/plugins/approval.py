"""Approval system Owner-only untuk user yang berhasil login."""

from __future__ import annotations

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import OWNER_ID
from database import approve_user, get_user, reject_user
from formatter import display_date, display_username
from logger import log, safe_handler
from runner import get_runner


def _approval_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Setujui",
                    callback_data=f"approval:approve:{telegram_id}",
                ),
                InlineKeyboardButton(
                    "❌ Tolak",
                    callback_data=f"approval:reject:{telegram_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "👤 Detail",
                    callback_data=f"approval:detail:{telegram_id}",
                )
            ],
        ]
    )


def _detail_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅️ Kembali",
                    callback_data=f"approval:back:{telegram_id}",
                )
            ]
        ]
    )


def _approval_request_text(user_data: dict) -> str:
    return (
        "╭─「 📥 𝗣𝗘𝗥𝗠𝗜𝗡𝗧𝗔𝗔𝗡 𝗕𝗔𝗥𝗨 」\n│\n"
        f"├ 👤 𝗡𝗮𝗺𝗮\n│  ╰➤ {user_data.get('full_name') or 'Tidak diketahui'}\n"
        f"├ 🔗 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲\n│  ╰➤ {display_username(user_data.get('username'))}\n"
        f"├ 🆔 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗜𝗗\n│  ╰➤ {user_data.get('telegram_id')}\n"
        f"├ 📱 𝗡𝗼𝗺𝗼𝗿\n│  ╰➤ {user_data.get('phone_number') or 'Tidak tersedia'}\n"
        f"├ 🕒 𝗪𝗮𝗸𝘁𝘂 𝗟𝗼𝗴𝗶𝗻\n│  ╰➤ {display_date(user_data.get('login_at'))}\n"
        "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
    )


def _detail_text(user_data: dict) -> str:
    return (
        "╭─「 👤 𝗗𝗘𝗧𝗔𝗜𝗟 𝗣𝗘𝗡𝗚𝗚𝗨𝗡𝗔 」\n│\n"
        f"├ 👤 𝗡𝗮𝗺𝗮\n│  ╰➤ {user_data.get('full_name') or 'Tidak diketahui'}\n"
        f"├ 🔗 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲\n│  ╰➤ {display_username(user_data.get('username'))}\n"
        f"├ 🆔 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗜𝗗\n│  ╰➤ {user_data.get('telegram_id')}\n"
        f"├ 📱 𝗡𝗼𝗺𝗼𝗿\n│  ╰➤ {user_data.get('phone_number') or 'Tidak tersedia'}\n"
        f"├ 📅 𝗧𝗮𝗻𝗴𝗴𝗮𝗹 𝗟𝗼𝗴𝗶𝗻\n│  ╰➤ {display_date(user_data.get('login_at'))}\n"
        f"├ ✅ 𝗦𝘁𝗮𝘁𝘂𝘀 𝗔𝗽𝗽𝗿𝗼𝘃𝗮𝗹\n│  ╰➤ {user_data.get('approval_status') or 'pending'}\n"
        "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
    )


def _with_status(user_data: dict, status: str, emoji: str) -> str:
    return (
        f"╭─「 {emoji} 𝗣𝗘𝗥𝗠𝗜𝗡𝗧𝗔𝗔𝗡 𝗕𝗔𝗥𝗨 」\n│\n"
        f"├ 👤 𝗡𝗮𝗺𝗮\n│  ╰➤ {user_data.get('full_name') or 'Tidak diketahui'}\n"
        f"├ 🆔 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗜𝗗\n│  ╰➤ {user_data.get('telegram_id')}\n"
        f"├ 📱 𝗡𝗼𝗺𝗼𝗿\n│  ╰➤ {user_data.get('phone_number') or 'Tidak tersedia'}\n"
        f"├ 🕒 𝗪𝗮𝗸𝘁𝘂 𝗟𝗼𝗴𝗶𝗻\n│  ╰➤ {display_date(user_data.get('login_at'))}\n"
        f"├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ {status}\n"
        "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱"
    )


async def notify_owner(client, telegram_id: int) -> None:
    """Kirim satu notifikasi approval tanpa pernah mengirim session."""
    if not OWNER_ID:
        log.error("OWNER_ID belum dikonfigurasi; notifikasi approval tidak terkirim.")
        return
    user_data = get_user(telegram_id)
    if not user_data:
        log.error("User %s tidak ditemukan saat mengirim approval.", telegram_id)
        return
    try:
        await client.send_message(
            OWNER_ID,
            _approval_request_text(user_data),
            reply_markup=_approval_keyboard(telegram_id),
        )
    except Exception:
        log.exception("Gagal mengirim notifikasi approval untuk user %s.", telegram_id)


async def _notify_user(client, telegram_id: int, text: str) -> None:
    try:
        await client.send_message(
            telegram_id,
            "╭─「 🔐 𝗦𝗧𝗔𝗧𝗨𝗦 𝗔𝗞𝗦𝗘𝗦 」\n│\n"
            f"├ 📌 𝗦𝘁𝗮𝘁𝘂𝘀\n│  ╰➤ {text}\n"
            "│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱",
        )
    except Exception:
        log.exception("Gagal mengirim hasil approval ke user %s.", telegram_id)


def _is_owner(query) -> bool:
    return bool(OWNER_ID and query.from_user and query.from_user.id == OWNER_ID)


def setup(client):
    @client.on_callback_query(filters.regex(r"^approval:(approve|reject|detail|back):\d+$"))
    @safe_handler
    async def approval_callback(client, query):
        if not _is_owner(query):
            await query.answer("⛔ Akses ditolak.", show_alert=True)
            log.warning(
                "Callback approval ditolak untuk user %s.",
                getattr(query.from_user, "id", "unknown"),
            )
            return

        parts = query.data.split(":")
        action = parts[1]
        telegram_id = int(parts[2])
        user_data = get_user(telegram_id)
        if not user_data:
            await query.answer("User tidak ditemukan.", show_alert=True)
            return

        await query.answer()
        if not query.message:
            return

        if action == "detail":
            await query.message.edit(
                _detail_text(user_data),
                reply_markup=_detail_keyboard(telegram_id),
            )
            return

        if action == "back":
            await query.message.edit(
                _approval_request_text(user_data),
                reply_markup=_approval_keyboard(telegram_id),
            )
            return

        if action == "approve":
            updated = approve_user(telegram_id, OWNER_ID)
            if not updated:
                await query.message.edit(
                    _with_status(user_data, "sudah diproses.", "ℹ️"),
                    reply_markup=None,
                )
                return
            await query.message.edit(
                _with_status(updated, "approved.", "✅"),
                reply_markup=None,
            )
            await _notify_user(
                client,
                telegram_id,
                "━━━━━━━━━━━━━━━━━━\n\n"
                "🎉 Selamat!\n\n"
                "Permintaan Anda telah disetujui.\n\n"
                "Status:\n"
                "🟢 Active\n\n"
                "Anda sekarang dapat menggunakan layanan IBEKS USERBOT.\n\n"
                "━━━━━━━━━━━━━━━━━━",
            )
            runner = get_runner()
            if runner:
                runner.sync_user(telegram_id)
            return

        updated = reject_user(telegram_id)
        if not updated:
            await query.message.edit(
                _with_status(user_data, "user tidak ditemukan.", "ℹ️"),
                reply_markup=None,
            )
            return
        await query.message.edit(
            _with_status(updated, "rejected.", "❌"),
            reply_markup=None,
        )
        await _notify_user(
            client,
            telegram_id,
            "━━━━━━━━━━━━━━━━━━\n\n"
            "❌ Permintaan Anda ditolak oleh Admin.\n\n"
            "Silakan hubungi Admin jika merasa terjadi kesalahan.\n\n"
            "━━━━━━━━━━━━━━━━━━",
        )
        runner = get_runner()
        if runner:
            runner.sync_user(telegram_id)
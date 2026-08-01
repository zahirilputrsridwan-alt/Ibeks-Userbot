"""UI Panel Admin Manager Bot."""

from __future__ import annotations

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from admin import (
    admin_activate,
    admin_delete,
    admin_extend,
    admin_statistics,
    admin_suspend,
    admin_user_detail,
    admin_users,
    is_owner,
)
from database import list_users, log_admin_activity
from engine import remove_userbot_runtime, stop_userbot
from formatter import display_date, display_username
from logger import log, safe_handler
from membership import membership_info

_INPUT_STATES: dict[int, str] = {}
_DELETE_CONFIRM: set[tuple[int, int]] = set()


def _button(text: str, action: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=f"manager:admin:{action}")


def panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [_button("👥 Daftar User", "users"), _button("📊 Statistik", "stats")],
            [_button("🔎 Detail User", "detail"), _button("⏳ Perpanjang", "extend")],
            [_button("⛔ Suspend User", "suspend"), _button("✅ Aktifkan User", "activate")],
            [_button("🗑 Hapus User", "delete"), _button("📢 Broadcast", "broadcast")],
            [_button("🏠 Menu Utama", "home")],
        ]
    )


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_button("⬅ Admin Panel", "menu")]])


def _user_line(user: dict) -> str:
    membership = membership_info(user)
    suspended = "⛔ Suspended" if user.get("suspended") else "✅ Active"
    return (
        f"`{user['telegram_id']}` — {user.get('full_name') or 'Tanpa nama'} "
        f"({membership['status']}, {suspended})"
    )


def _users_text(users: list[dict]) -> str:
    if not users:
        return "👥 **Daftar User**\n\nBelum ada user terdaftar."
    lines = ["👥 **Daftar User**", ""]
    lines.extend(f"{index}. {_user_line(user)}" for index, user in enumerate(users, 1))
    return "\n".join(lines)


def _detail_text(user: dict | None) -> str:
    if not user:
        return "❌ User tidak ditemukan."
    membership = membership_info(user)
    return (
        "🔎 **Detail User**\n\n"
        f"• ID : `{user['telegram_id']}`\n"
        f"• Nama : {user.get('full_name') or 'Tidak diketahui'}\n"
        f"• Username : {display_username(user.get('username'))}\n"
        f"• Status Login : {user.get('status') or 'Belum Aktif'}\n"
        f"• Status Suspend : {'Suspended' if user.get('suspended') else 'Active'}\n"
        f"• Membership : {membership['status']}\n"
        f"• Berakhir : {display_date(membership['expired_at'])}\n"
        f"• Sisa Hari : {membership['days_remaining']}\n"
        f"• Userbot : {user.get('userbot_status') or '🔴 Offline'}\n"
        f"• Login : {display_date(user.get('login_at'))}"
    )


def _stats_text(stats: dict[str, int]) -> str:
    return (
        "📊 **Statistik**\n\n"
        f"• Total User : {stats['total']}\n"
        f"• User Aktif : {stats['active']}\n"
        f"• User Expired : {stats['expired']}\n"
        f"• User Online : {stats['online']}\n"
        f"• User Offline : {stats['offline']}"
    )


def _input_prompt(action: str) -> str:
    prompts = {
        "detail": "Kirim Telegram ID user yang ingin dilihat.",
        "extend": "Kirim Telegram ID user yang ingin diperpanjang.",
        "suspend": "Kirim Telegram ID user yang ingin disuspend.",
        "activate": "Kirim Telegram ID user yang ingin diaktifkan.",
        "delete": "Kirim Telegram ID user yang ingin dihapus.",
        "broadcast": "Kirim pesan atau media yang ingin dibroadcast ke semua user.",
    }
    return f"🛠 Admin\n\n{prompts[action]}\n\nKirim /cancel untuk membatalkan."


async def _show_panel(query) -> None:
    await query.message.edit(
        "🛠 **Admin Panel**\n\nPilih operasi yang ingin dilakukan.",
        reply_markup=panel_keyboard(),
    )


def _parse_user_id(message) -> int | None:
    try:
        return int((message.text or "").strip())
    except (TypeError, ValueError):
        return None


def _admin_input_filter(_, __, message) -> bool:
    """Cocokkan hanya pesan Owner saat ada operasi input Admin aktif."""
    return bool(
        message
        and message.from_user
        and is_owner(message.from_user.id)
        and _INPUT_STATES.get(message.from_user.id)
    )


def setup(client):
    @client.on_callback_query(
        filters.regex(
            r"^manager:admin(?::(menu|home|users|stats|detail|extend|suspend|activate|delete|broadcast))?$"
        )
    )
    @safe_handler
    async def admin_callback(client, query):
        if not query.from_user or not is_owner(query.from_user.id):
            if query.from_user:
                log_admin_activity(query.from_user.id, "access_denied")
            await query.answer("Akses Admin ditolak.", show_alert=True)
            return
        await query.answer()
        action = (query.data or "manager:admin:menu").split(":")[-1]
        admin_id = query.from_user.id
        if action in {"admin", "menu", "home"}:
            if action == "home":
                from plugins.start.start import main_keyboard

                await query.message.edit(
                    "👋 **Selamat Datang di IBEKS USERBOT**\n\nSilakan pilih menu di bawah.",
                    reply_markup=main_keyboard(admin_id),
                )
            else:
                await _show_panel(query)
            return
        if action == "users":
            await query.message.edit(_users_text(admin_users(admin_id)), reply_markup=_back_keyboard())
        elif action == "stats":
            await query.message.edit(_stats_text(admin_statistics(admin_id)), reply_markup=_back_keyboard())
        elif action in {"detail", "extend", "suspend", "activate", "delete", "broadcast"}:
            _INPUT_STATES[admin_id] = action
            await query.message.edit(_input_prompt(action), reply_markup=_back_keyboard())

    @client.on_message(
        filters.private
        & filters.incoming
        & filters.create(_admin_input_filter, "AdminInput"),
        group=-2,
    )
    @safe_handler
    async def admin_input_handler(client, message):
        if not message.from_user or not is_owner(message.from_user.id):
            return
        action = _INPUT_STATES.get(message.from_user.id)
        if not action:
            return
        admin_id = message.from_user.id
        if (message.text or "").strip().lower() == "/cancel":
            _INPUT_STATES.pop(admin_id, None)
            await message.reply("✅ Operasi Admin dibatalkan.", reply_markup=panel_keyboard())
            return
        if action == "broadcast":
            recipients = list_users()
            sent = 0
            failed = 0
            for user in recipients:
                try:
                    await client.copy_message(user["telegram_id"], message.chat.id, message.id)
                    sent += 1
                except Exception as exc:
                    failed += 1
                    log.warning("Broadcast ke %s gagal: %s", user["telegram_id"], exc)
            log_admin_activity(admin_id, "broadcast", details=f"sent={sent},failed={failed}")
            _INPUT_STATES.pop(admin_id, None)
            await message.reply(
                f"📢 Broadcast selesai.\n\n✅ Berhasil: {sent}\n❌ Gagal: {failed}",
                reply_markup=panel_keyboard(),
            )
            return

        user_id = _parse_user_id(message)
        if user_id is None:
            await message.reply("❌ Telegram ID harus berupa angka.")
            return
        if action == "detail":
            _INPUT_STATES.pop(admin_id, None)
            await message.reply(_detail_text(admin_user_detail(admin_id, user_id)), reply_markup=panel_keyboard())
        elif action == "extend":
            _INPUT_STATES.pop(admin_id, None)
            await message.reply("Pilih masa perpanjangan:", reply_markup=_extend_keyboard(user_id))
        elif action in {"suspend", "activate"}:
            _INPUT_STATES.pop(admin_id, None)
            if action == "suspend":
                if user_id == admin_id:
                    await message.reply("❌ Owner tidak dapat disuspend.", reply_markup=panel_keyboard())
                else:
                    changed = admin_suspend(admin_id, user_id)
                    if changed:
                        await stop_userbot(user_id)
                    await message.reply("✅ User disuspend." if changed else "❌ User tidak ditemukan.", reply_markup=panel_keyboard())
            else:
                changed = admin_activate(admin_id, user_id)
                await message.reply("✅ User diaktifkan." if changed else "❌ User tidak ditemukan.", reply_markup=panel_keyboard())
        elif action == "delete":
            _INPUT_STATES.pop(admin_id, None)
            if user_id == admin_id:
                await message.reply("❌ Owner tidak dapat dihapus.", reply_markup=panel_keyboard())
            else:
                _DELETE_CONFIRM.add((admin_id, user_id))
                await message.reply(
                    f"⚠️ Hapus user `{user_id}`? Tindakan ini tidak dapat dibatalkan.",
                    reply_markup=_confirm_delete_keyboard(user_id),
                )

    @client.on_callback_query(filters.regex(r"^manager:admin:extend:\d+:\d+$"))
    @safe_handler
    async def extend_callback(client, query):
        if not query.from_user or not is_owner(query.from_user.id):
            if query.from_user:
                log_admin_activity(query.from_user.id, "access_denied")
            await query.answer("Akses Admin ditolak.", show_alert=True)
            return
        await query.answer()
        _, _, _, user_id, days = (query.data or "").split(":")
        admin_id = query.from_user.id
        _INPUT_STATES.pop(admin_id, None)
        try:
            expired_at = admin_extend(admin_id, int(user_id), int(days))
            await query.message.edit(
                f"✅ Membership `{user_id}` diperpanjang {days} hari.\n"
                f"Berakhir: {display_date(expired_at)}",
                reply_markup=panel_keyboard(),
            )
        except ValueError as exc:
            await query.message.edit(f"❌ {exc}", reply_markup=panel_keyboard())

    @client.on_callback_query(filters.regex(r"^manager:admin:delete:\d+:(confirm|cancel)$"))
    @safe_handler
    async def delete_callback(client, query):
        if not query.from_user or not is_owner(query.from_user.id):
            if query.from_user:
                log_admin_activity(query.from_user.id, "access_denied")
            await query.answer("Akses Admin ditolak.", show_alert=True)
            return
        await query.answer()
        _, _, _, user_id, decision = (query.data or "").split(":")
        admin_id = query.from_user.id
        user_id_int = int(user_id)
        _DELETE_CONFIRM.discard((admin_id, user_id_int))
        if decision == "cancel":
            await query.message.edit("✅ Penghapusan dibatalkan.", reply_markup=panel_keyboard())
            return
        await stop_userbot(user_id_int)
        deleted = admin_delete(admin_id, user_id_int)
        if deleted:
            remove_userbot_runtime(user_id_int)
        await query.message.edit(
            "✅ User berhasil dihapus." if deleted else "❌ User tidak ditemukan.",
            reply_markup=panel_keyboard(),
        )


def _extend_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("＋7 Hari", callback_data=f"manager:admin:extend:{user_id}:7"),
                InlineKeyboardButton("＋30 Hari", callback_data=f"manager:admin:extend:{user_id}:30"),
            ],
            [
                InlineKeyboardButton("＋90 Hari", callback_data=f"manager:admin:extend:{user_id}:90"),
                InlineKeyboardButton("＋365 Hari", callback_data=f"manager:admin:extend:{user_id}:365"),
            ],
            [_button("⬅ Admin Panel", "menu")],
        ]
    )


def _confirm_delete_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "✅ Ya, Hapus",
                callback_data=f"manager:admin:delete:{user_id}:confirm",
            ),
            InlineKeyboardButton(
                "✖ Batal",
                callback_data=f"manager:admin:delete:{user_id}:cancel",
            ),
        ]]
    )
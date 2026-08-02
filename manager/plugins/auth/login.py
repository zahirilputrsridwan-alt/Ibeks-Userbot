"""Login akun Telegram dengan state sementara per pengguna Manager."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberInvalid,
    SessionPasswordNeeded,
)
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import API_HASH, API_ID
from database import (
    get_or_create_user,
    mark_login_failed,
    mark_login_pending,
    save_login_success,
)
from formatter import full_name
from logger import log, safe_handler
from plugins.approval import notify_owner
from plugins.start.start import home_keyboard


PHONE_PATTERN = re.compile(r"^\+\d{7,15}$")
LOGIN_STAGES = {"phone", "code", "password"}


@dataclass
class LoginState:
    """Data login yang hanya hidup selama satu percobaan autentikasi."""

    telegram_id: int
    stage: str = "phone"
    phone_number: str | None = None
    phone_code_hash: str | None = None
    client: Client | None = None
    code_message: Message | None = None
    password_message: Message | None = None


_login_states: dict[int, LoginState] = {}


def _login_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Batalkan", callback_data="manager:login_cancel")]]
    )


def _phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📱 Kirim Nomor Saya", request_contact=True)],
            [KeyboardButton("❌ Batalkan")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _normalize_contact_phone(phone_number: str | None) -> str | None:
    """Normalisasi nomor dari Contact Telegram tanpa menerima input manual."""
    if not phone_number:
        return None
    normalized = re.sub(r"[ ()-]", "", phone_number.strip())
    if normalized.startswith("00"):
        normalized = "+" + normalized[2:]
    elif normalized.isdigit():
        normalized = "+" + normalized
    return normalized if PHONE_PATTERN.fullmatch(normalized) else None


async def _safe_disconnect(client: Client | None) -> None:
    if client is None:
        return
    try:
        if client.is_connected:
            await client.disconnect()
    except Exception:
        log.exception("Gagal menutup client login Telegram.")


async def _delete_message(message: Message | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except Exception:
        # Pesan bisa sudah dihapus atau tidak dapat dihapus oleh bot.
        log.debug("Pesan input login tidak dapat dihapus.")


async def _finish_state(telegram_id: int) -> LoginState | None:
    state = _login_states.pop(telegram_id, None)
    if state:
        await _safe_disconnect(state.client)
    return state


async def begin_login(user, message: Message) -> None:
    """Mulai percobaan login dan minta nomor telepon."""
    telegram_id = user.id
    get_or_create_user(telegram_id, user.username, full_name(user))
    await _finish_state(telegram_id)
    _login_states[telegram_id] = LoginState(telegram_id=telegram_id)
    mark_login_pending(telegram_id, "")
    await message.edit("📲 Minta Akses\n\nMenunggu nomor Telegram Anda.")
    await message.reply(
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📱 Kirim Nomor Telegram\n\n"
        'Silakan tekan tombol "Kirim Nomor Saya".\n\n'
        "Telegram akan mengirim nomor Anda secara otomatis.\n\n"
        "━━━━━━━━━━━━━━━━━━",
        reply_markup=_phone_request_keyboard(),
    )


async def _send_code(
    state: LoginState,
    message: Message,
    phone_number: str,
) -> None:
    client = Client(
        name=f"ibeks_login_{state.telegram_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
    )
    try:
        await client.connect()
        sent_code = await client.send_code(phone_number)
    except PhoneNumberInvalid:
        log.warning("PhoneNumberInvalid pada login user %s.", state.telegram_id)
        await _safe_disconnect(client)
        mark_login_failed(state.telegram_id)
        _login_states.pop(state.telegram_id, None)
        await message.reply(
            "❌ Nomor Telegram tidak valid. Silakan mulai lagi.",
            reply_markup=home_keyboard(),
        )
        return
    except FloodWait as error:
        log.warning(
            "FloodWait saat mengirim kode login untuk user %s: %ss.",
            state.telegram_id,
            error.value,
        )
        await _safe_disconnect(client)
        mark_login_failed(state.telegram_id)
        _login_states.pop(state.telegram_id, None)
        await message.reply(
            f"⏳ Terlalu banyak percobaan. Coba lagi dalam {error.value} detik.",
            reply_markup=home_keyboard(),
        )
        return
    except Exception:
        log.exception("Error saat mengirim kode login untuk user %s.", state.telegram_id)
        await _safe_disconnect(client)
        mark_login_failed(state.telegram_id)
        _login_states.pop(state.telegram_id, None)
        await message.reply(
            "❌ Kode login tidak dapat dikirim. Silakan coba lagi.",
            reply_markup=home_keyboard(),
        )
        return

    state.phone_number = phone_number
    state.phone_code_hash = sent_code.phone_code_hash
    state.client = client
    state.stage = "code"
    mark_login_pending(state.telegram_id, phone_number)
    await message.reply(
        "🔐 Kode login sudah dikirim oleh Telegram.\n\n"
        "Masukkan kode yang Anda terima.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def _complete_login(
    state: LoginState,
    message: Message,
    manager_client: Client,
) -> None:
    if state.client is None or not state.phone_number:
        raise RuntimeError("State login tidak lengkap.")
    session_string = await state.client.export_session_string()
    if not session_string:
        raise RuntimeError("Session string kosong setelah login berhasil.")
    save_login_success(state.telegram_id, state.phone_number, session_string)
    await _delete_message(state.code_message)
    await _delete_message(state.password_message)
    await _finish_state(state.telegram_id)
    await message.reply(
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ Permintaan Anda berhasil dikirim.\n\n"
        "Mohon tunggu hingga Admin menyetujui akun Anda.\n\n"
        "Status:\n"
        "🟡 Menunggu Persetujuan\n\n"
        "━━━━━━━━━━━━━━━━━━",
        reply_markup=home_keyboard(),
    )
    await notify_owner(manager_client, state.telegram_id)


async def _check_code(
    state: LoginState,
    message: Message,
    manager_client: Client,
) -> None:
    if state.client is None or not state.phone_number or not state.phone_code_hash:
        raise RuntimeError("State kode login tidak lengkap.")
    state.code_message = message
    try:
        await state.client.sign_in(
            state.phone_number,
            state.phone_code_hash,
            (message.text or "").strip().replace(" ", ""),
        )
    except SessionPasswordNeeded:
        state.stage = "password"
        await message.reply(
            "🔒 Akun ini menggunakan Password 2FA.\n\n"
            "Masukkan Password 2FA Anda.",
            reply_markup=_login_keyboard(),
        )
        return
    except PhoneCodeInvalid:
        log.warning("PhoneCodeInvalid pada login user %s.", state.telegram_id)
        await message.reply(
            "❌ Kode salah. Silakan masukkan kode yang benar.",
            reply_markup=_login_keyboard(),
        )
        return
    except PhoneCodeExpired:
        log.warning("OTP kedaluwarsa pada login user %s.", state.telegram_id)
        await _finish_state(state.telegram_id)
        mark_login_failed(state.telegram_id)
        await message.reply(
            "⌛ Kode login sudah kedaluwarsa. Silakan mulai lagi.",
            reply_markup=home_keyboard(),
        )
        return
    except FloodWait as error:
        log.warning(
            "FloodWait saat verifikasi kode untuk user %s: %ss.",
            state.telegram_id,
            error.value,
        )
        await _finish_state(state.telegram_id)
        mark_login_failed(state.telegram_id)
        await message.reply(
            f"⏳ Terlalu banyak percobaan. Coba lagi dalam {error.value} detik.",
            reply_markup=home_keyboard(),
        )
        return
    except Exception:
        log.exception("Error tak terduga saat verifikasi kode untuk user %s.", state.telegram_id)
        await _finish_state(state.telegram_id)
        mark_login_failed(state.telegram_id)
        await message.reply(
            "❌ Verifikasi login gagal. Silakan mulai lagi.",
            reply_markup=home_keyboard(),
        )
        return

    try:
        await _complete_login(state, message, manager_client)
    except Exception:
        log.exception("Error saat menyimpan session login user %s.", state.telegram_id)
        await _finish_state(state.telegram_id)
        mark_login_failed(state.telegram_id)
        await message.reply(
            "❌ Login belum dapat diselesaikan. Silakan mulai lagi.",
            reply_markup=home_keyboard(),
        )


async def _check_password(
    state: LoginState,
    message: Message,
    manager_client: Client,
) -> None:
    if state.client is None:
        raise RuntimeError("State client login tidak lengkap.")
    state.password_message = message
    try:
        await state.client.check_password((message.text or "").strip())
    except PasswordHashInvalid:
        log.warning("PasswordHashInvalid pada login user %s.", state.telegram_id)
        await message.reply(
            "❌ Password 2FA salah. Silakan coba lagi.",
            reply_markup=_login_keyboard(),
        )
        return
    except FloodWait as error:
        log.warning(
            "FloodWait saat verifikasi password untuk user %s: %ss.",
            state.telegram_id,
            error.value,
        )
        await _finish_state(state.telegram_id)
        mark_login_failed(state.telegram_id)
        await message.reply(
            f"⏳ Terlalu banyak percobaan. Coba lagi dalam {error.value} detik.",
            reply_markup=home_keyboard(),
        )
        return
    except Exception:
        log.exception("Error tak terduga saat verifikasi password user %s.", state.telegram_id)
        await _finish_state(state.telegram_id)
        mark_login_failed(state.telegram_id)
        await message.reply(
            "❌ Verifikasi Password 2FA gagal. Silakan mulai lagi.",
            reply_markup=home_keyboard(),
        )
        return

    try:
        await _complete_login(state, message, manager_client)
    except Exception:
        log.exception("Error saat menyimpan session 2FA user %s.", state.telegram_id)
        await _finish_state(state.telegram_id)
        mark_login_failed(state.telegram_id)
        await message.reply(
            "❌ Login belum dapat diselesaikan. Silakan mulai lagi.",
            reply_markup=home_keyboard(),
        )


def setup(client):
    @client.on_callback_query(filters.regex(r"^manager:login_cancel$"))
    @safe_handler
    async def cancel_login_callback(client, query):
        await query.answer()
        if not query.from_user:
            return
        state = await _finish_state(query.from_user.id)
        if state:
            mark_login_failed(query.from_user.id)
        if query.message:
            await query.message.edit(
                "❌ Proses login dibatalkan.",
                reply_markup=home_keyboard(),
            )

    @client.on_message(
        filters.private & filters.contact,
        group=0,
    )
    @safe_handler
    async def login_contact_handler(client, message):
        if not message.from_user or not message.contact:
            return
        state = _login_states.get(message.from_user.id)
        if not state or state.stage != "phone":
            return

        contact = message.contact
        if contact.user_id != message.from_user.id:
            await message.reply(
                '❌ Gunakan tombol "Kirim Nomor Saya".',
                reply_markup=_phone_request_keyboard(),
            )
            return

        phone_number = _normalize_contact_phone(contact.phone_number)
        if not phone_number:
            log.warning(
                "Contact Telegram tidak valid pada login user %s.",
                message.from_user.id,
            )
            await message.reply(
                "❌ Nomor Telegram tidak valid. Silakan gunakan tombol lagi.",
                reply_markup=_phone_request_keyboard(),
            )
            return

        await _send_code(state, message, phone_number)

    @client.on_message(
        filters.private & filters.text & ~filters.command("start"),
        group=0,
    )
    @safe_handler
    async def login_message_handler(client, message):
        if not message.from_user or not message.text:
            return
        state = _login_states.get(message.from_user.id)
        if not state or state.stage not in LOGIN_STAGES:
            return
        if state.stage == "phone":
            if message.text.strip() == "❌ Batalkan":
                await _finish_state(message.from_user.id)
                mark_login_failed(message.from_user.id)
                await message.reply(
                    "❌ Proses login dibatalkan.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return
            await message.reply(
                '❌ Gunakan tombol "Kirim Nomor Saya".',
                reply_markup=_phone_request_keyboard(),
            )
        elif state.stage == "code":
            await _check_code(state, message, client)
        elif state.stage == "password":
            await _check_password(state, message, client)
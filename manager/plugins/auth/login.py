"""Login akun Telegram pengguna melalui percakapan bertahap yang aman."""

from __future__ import annotations

import asyncio
import re
import time
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
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import API_HASH, API_ID, LOGIN_TIMEOUT_SECONDS
from database import get_or_create_user, save_login
from engine import start_userbot, stop_userbot
from formatter import full_name
from logger import log, safe_handler
from plugins.start.start import home_keyboard
from plugins.terminal.userbot import account_keyboard

_PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")
_OTP_RE = re.compile(r"^\d{5,6}$")
_ACTIVE_LOGINS: dict[int, "LoginState"] = {}
_STATE_LOCK = asyncio.Lock()


@dataclass
class LoginState:
    """State sementara satu percakapan login."""

    manager_user_id: int
    client: Client | None = None
    phone_number: str | None = None
    phone_code_hash: str | None = None
    stage: str = "phone"
    expires_at: float = 0.0
    cleanup_task: asyncio.Task | None = None


def _phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Bagikan Nomor", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✖ Batalkan Login", callback_data="manager:login_cancel")]]
    )


def _normalize_phone(value: str) -> str:
    return re.sub(r"[\s()\-]", "", value.strip())


def _normalize_otp(value: str) -> str:
    return re.sub(r"\D", "", value)


async def _remove_state(user_id: int) -> LoginState | None:
    async with _STATE_LOCK:
        state = _ACTIVE_LOGINS.pop(user_id, None)
    if state and state.cleanup_task and state.cleanup_task is not asyncio.current_task():
        state.cleanup_task.cancel()
    if state and state.client:
        try:
            if state.client.is_connected:
                await state.client.disconnect()
        except Exception as exc:
            log.warning("Gagal membersihkan client login user %s: %s", user_id, exc)
    if state:
        # Hapus referensi OTP/hash/nomor dari state sesegera mungkin.
        state.phone_code_hash = None
        state.phone_number = None
        state.client = None
    return state


async def _expire_login(client, user_id: int) -> None:
    try:
        await asyncio.sleep(LOGIN_TIMEOUT_SECONDS)
        state = _ACTIVE_LOGINS.get(user_id)
        if state:
            await _remove_state(user_id)
            await client.send_message(
                user_id,
                "⌛ Sesi login berakhir karena timeout. Silakan mulai ulang dari menu.",
                reply_markup=home_keyboard(),
            )
    except asyncio.CancelledError:
        return
    except Exception as exc:
        log.exception("Gagal mengirim notifikasi timeout login user %s: %s", user_id, exc)


async def _send_phone_prompt(client, user_id: int) -> None:
    await client.send_message(
        user_id,
        "📲 Kirim nomor Telegram Anda.\n\n"
        "Gunakan tombol Bagikan Nomor atau ketik manual dengan format "
        "`+628xxxxxxxxxx`.",
        reply_markup=_phone_keyboard(),
    )


async def _start_login(client, query) -> None:
    user = query.from_user
    if not user:
        return
    user_id = user.id
    await _remove_state(user_id)
    state = LoginState(
        manager_user_id=user_id,
        expires_at=time.monotonic() + LOGIN_TIMEOUT_SECONDS,
    )
    async with _STATE_LOCK:
        _ACTIVE_LOGINS[user_id] = state
    state.cleanup_task = asyncio.create_task(_expire_login(client, user_id))
    await _send_phone_prompt(client, user_id)


async def _handle_phone(client, message, state: LoginState) -> None:
    contact = message.contact
    if contact:
        if contact.user_id and contact.user_id != message.from_user.id:
            await message.reply("❌ Silakan bagikan kontak milik akun Anda sendiri.")
            return
        raw_phone = contact.phone_number
    else:
        raw_phone = message.text or ""

    phone = _normalize_phone(raw_phone)
    if contact and phone and not phone.startswith("+"):
        phone = f"+{phone}"
    if not _PHONE_RE.fullmatch(phone):
        await message.reply(
            "❌ Format nomor tidak valid.\n\n"
            "Kirim ulang dengan format internasional, contoh: `+628xxxxxxxxxx`.",
            reply_markup=_phone_keyboard(),
        )
        return

    user_client = Client(
        name=f"manager_login_{message.from_user.id}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
        no_updates=True,
    )
    try:
        await user_client.connect()
        sent_code = await user_client.send_code(phone)
    except PhoneNumberInvalid:
        await user_client.disconnect()
        await message.reply(
            "❌ Nomor Telegram tidak valid atau tidak dapat digunakan. Kirim ulang.",
            reply_markup=_phone_keyboard(),
        )
        return
    except FloodWait as exc:
        await user_client.disconnect()
        await _remove_state(message.from_user.id)
        await message.reply(
            f"⏳ Terlalu banyak percobaan. Coba lagi dalam {exc.value} detik.",
            reply_markup=home_keyboard(),
        )
        return
    except Exception:
        await user_client.disconnect()
        await _remove_state(message.from_user.id)
        log.exception("Gagal mengirim kode login user %s", message.from_user.id)
        await message.reply("❌ Kode verifikasi gagal dikirim. Silakan coba lagi.")
        return

    state.client = user_client
    state.phone_number = phone
    state.phone_code_hash = sent_code.phone_code_hash
    state.stage = "otp"
    await message.reply(
        "✅ Kode verifikasi telah dikirim ke akun Telegram Anda.\n\n"
        "Kirim kode OTP, contoh `1 2 3 4 5` atau `12345`.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def _finish_login(message, state: LoginState, logged_user) -> None:
    session_string = await state.client.export_session_string()
    if not hasattr(logged_user, "id"):
        logged_user = await state.client.get_me()
    await stop_userbot(message.from_user.id)
    save_login(
        telegram_id=message.from_user.id,
        phone_number=state.phone_number or "",
        session_string=session_string,
        username=logged_user.username,
        full_name=" ".join(
            part for part in [logged_user.first_name, logged_user.last_name] if part
        ) or logged_user.username or "Pengguna Telegram",
    )
    await _remove_state(message.from_user.id)
    started, start_result = await start_userbot(message.from_user.id)
    if started:
        result = "✅ Login Telegram berhasil.\n\n🟢 Userbot berhasil online."
    else:
        result = (
            "✅ Login Telegram berhasil.\n\n"
            f"🟡 Userbot belum online: {start_result}"
        )
    await message.reply(
        result,
        reply_markup=account_keyboard(),
    )


async def _handle_otp(client, message, state: LoginState) -> None:
    otp = _normalize_otp(message.text or "")
    if not _OTP_RE.fullmatch(otp):
        otp = ""
        await message.reply("❌ Format OTP tidak valid. Masukkan 5 atau 6 digit.")
        return
    try:
        logged_user = await state.client.sign_in(
            state.phone_number,
            state.phone_code_hash,
            otp,
        )
        await _finish_login(message, state, logged_user)
    except SessionPasswordNeeded:
        state.stage = "password"
        await message.reply(
            "🔐 Akun Anda menggunakan Password Dua Langkah.\n\n"
            "Silakan kirim Password Telegram Anda.",
            reply_markup=_cancel_keyboard(),
        )
    except PhoneCodeInvalid:
        await message.reply("❌ Kode OTP salah. Silakan masukkan ulang.")
    except PhoneCodeExpired:
        await _remove_state(message.from_user.id)
        await message.reply(
            "⌛ Kode OTP sudah kedaluwarsa. Silakan mulai proses login dari awal.",
            reply_markup=home_keyboard(),
        )
    except FloodWait as exc:
        await _remove_state(message.from_user.id)
        await message.reply(
            f"⏳ Terlalu banyak percobaan. Coba lagi dalam {exc.value} detik.",
            reply_markup=home_keyboard(),
        )
    except Exception:
        await _remove_state(message.from_user.id)
        log.exception("Login OTP gagal untuk user %s", message.from_user.id)
        await message.reply("❌ Login gagal dengan aman. Silakan mulai ulang.")
    finally:
        otp = ""


async def _handle_password(client, message, state: LoginState) -> None:
    password = message.text or ""
    if not password:
        await message.reply("❌ Password tidak boleh kosong.")
        return
    try:
        logged_user = await state.client.check_password(password)
        password = ""
        await _finish_login(message, state, logged_user)
    except PasswordHashInvalid:
        password = ""
        await message.reply("❌ Password Dua Langkah salah. Silakan coba lagi.")
    except FloodWait as exc:
        password = ""
        await _remove_state(message.from_user.id)
        await message.reply(
            f"⏳ Terlalu banyak percobaan. Coba lagi dalam {exc.value} detik.",
            reply_markup=home_keyboard(),
        )
    except Exception:
        password = ""
        await _remove_state(message.from_user.id)
        log.exception("Login password gagal untuk user %s", message.from_user.id)
        await message.reply("❌ Login gagal dengan aman. Silakan mulai ulang.")


def setup(client):
    """Daftarkan callback mulai/batal dan handler percakapan login."""

    @client.on_callback_query(filters.regex(r"^manager:request$"))
    @safe_handler
    async def request_access_callback(client, query):
        await query.answer()
        await _start_login(client, query)

    @client.on_callback_query(filters.regex(r"^manager:login_cancel$"))
    @safe_handler
    async def cancel_login_callback(client, query):
        await query.answer("Login dibatalkan.")
        if query.from_user:
            await _remove_state(query.from_user.id)
        if query.message:
            await query.message.edit(
                "❌ Proses login dibatalkan.",
                reply_markup=home_keyboard(),
            )

    @client.on_message(filters.private & filters.incoming)
    @safe_handler
    async def login_message_handler(client, message):
        if not message.from_user:
            return
        state = _ACTIVE_LOGINS.get(message.from_user.id)
        if not state:
            return
        if time.monotonic() > state.expires_at:
            await _remove_state(message.from_user.id)
            await message.reply(
                "⌛ Sesi login berakhir karena timeout. Silakan mulai ulang.",
                reply_markup=home_keyboard(),
            )
            return
        if state.stage == "phone":
            await _handle_phone(client, message, state)
        elif state.stage == "otp":
            await _handle_otp(client, message, state)
        elif state.stage == "password":
            await _handle_password(client, message, state)
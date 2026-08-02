"""
IBEKS USERBOT - Entry Point
Inisialisasi Pyrogram client, database, dan plugin loader.
"""

import sys
import os
import re

# Tambahkan direktori userbot ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyrogram
from pyrogram import Client, filters, idle
from pyrogram.errors import ApiIdInvalid, AuthKeyUnregistered, SessionRevoked

from config import API_ID, API_HASH, STRING_SESSION, BOT_NAME, VERSION, CMD_PREFIX, MAIN_FILE, RESTART_STATE_FILE
from db import init_db
from loader import load_plugins, plugin_filename
from utils.logger import log
from utils.prefix_manager import set_owner_id, get_prefix
from utils.error_handler import install_global_error_handler
from utils.voice_manager import voice_manager


_TELEGRAM_BOT_TOKEN_RE = re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b")


def _redact_debug_text(text: str) -> str:
    """Redaksi token Bot API sebelum pesan masuk ke log debug."""
    return _TELEGRAM_BOT_TOKEN_RE.sub("[TELEGRAM_BOT_TOKEN_REDACTED]", text)


def validate_config() -> None:
    """Pastikan semua konfigurasi wajib tersedia sebelum memulai."""
    errors = []
    if not API_ID:
        errors.append("API_ID belum di-set di Replit Secrets.")
    if not API_HASH:
        errors.append("API_HASH belum di-set di Replit Secrets.")
    if not STRING_SESSION:
        errors.append("STRING_SESSION belum di-set di Replit Secrets.")

    if errors:
        for err in errors:
            log.critical(f"[Config] {err}")
        sys.exit(1)


def _read_restart_state() -> dict:
    """Baca state restart dari file."""
    if not os.path.exists(RESTART_STATE_FILE):
        return {}
    try:
        with open(RESTART_STATE_FILE, "r", encoding="utf-8") as f:
            chat_id = f.read().strip()
        return {"chat_id": int(chat_id)} if chat_id else {}
    except Exception as exc:
        log.warning(f"[Main] Gagal membaca state restart: {exc}")
    return {}


def _clear_restart_state() -> None:
    """Hapus file state restart jika ada."""
    try:
        if os.path.exists(RESTART_STATE_FILE):
            os.remove(RESTART_STATE_FILE)
    except Exception as exc:
        log.warning(f"[Main] Gagal menghapus state restart: {exc}")


def log_startup_info(client, me, plugin_stats) -> None:
    """Tampilkan login, daftar plugin, dan total plugin saat startup."""
    owner = me.first_name or me.username or "Unknown"
    log.info("✓ Login berhasil")
    log.info("✓ Userbot aktif")
    log.info(f"Nama akun Telegram : {owner}")
    log.info(f"User ID            : {me.id}")
    log.info(f"Prefix             : {get_prefix()}")

    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🤖 {BOT_NAME}",
        "",
        "📦 Plugin Loaded",
        "",
    ]
    lines.extend(f"✅ {plugin_filename(module)}" for module in plugin_stats["loaded"])
    for failure in plugin_stats.get("failed_details", []):
        lines.append(f"❌ {failure['filename']}")
        lines.append(f"   {failure['error_type']}: {failure['reason']}")
    lines.extend(
        [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            f"📊 Total Plugin : {len(plugin_stats['loaded'])}",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
    )
    log.info("\n".join(lines))


def main() -> None:
    """Titik masuk utama IBEKS USERBOT."""
    log.info(f"╭━━━━━━━━━━━━━━━━━━━━━━╮")
    log.info(f"     💀 {BOT_NAME}")
    log.info(f"     📦 Version {VERSION}")
    log.info(f"╰━━━━━━━━━━━━━━━━━━━━━━╯")

    # ── Validasi konfigurasi ──────────────────────────────────────────────────
    validate_config()

    # ── Inisialisasi database ─────────────────────────────────────────────────
    init_db()

    # ── Buat Pyrogram client ──────────────────────────────────────────────────
    client = Client(
        name="ibeks_userbot",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=STRING_SESSION,
        in_memory=True,       # Tidak menyimpan file .session di disk
    )

    # ── Inisialisasi voice chat manager dengan client Pyrogram ───────────────
    voice_manager.set_client(client)

    # ── Pasang global error handler agar error plugin tidak merusak bot ───────
    install_global_error_handler()

    # ── Muat semua plugin ke instance client ──────────────────────────────────
    plugin_stats = load_plugins(client)

    # ── Debug handler: log semua pesan masuk (hanya log, tidak reply) ────────
    @client.on_message(filters.incoming)
    async def debug_incoming(_client, message):
        try:
            chat_id = message.chat.id if message.chat else "n/a"
            from_id = message.from_user.id if message.from_user else "n/a"
            text = _redact_debug_text(message.text or message.caption or "[no text]")
            log.info(f"[Debug] Incoming msg | chat={chat_id} from={from_id} text={text!r}")
        except Exception as exc:
            log.warning(f"[Debug] Gagal log pesan: {exc}")

    # ── Jalankan client ───────────────────────────────────────────────────────
    try:
        log.info("[Main] Menghubungkan ke Telegram...")
        client.start()

        me = client.get_me()
        # Cache owner ID untuk prefix manager dan utilities lain
        set_owner_id(me.id)

        log_startup_info(client, me, plugin_stats)

        # Kirim notifikasi restart jika bot baru saja dihidupkan ulang
        restart_state = _read_restart_state()
        if restart_state:
            try:
                client.send_message(restart_state["chat_id"], "✅ Userbot berhasil direstart.")
            except Exception as exc:
                log.warning(f"[Main] Gagal mengirim pesan restart: {exc}")
            _clear_restart_state()

        idle()
    except ApiIdInvalid:
        log.critical("[Main] API_ID atau API_HASH tidak valid. Periksa Replit Secrets.")
        sys.exit(1)
    except AuthKeyUnregistered:
        log.critical("[Main] STRING_SESSION tidak valid atau sudah kedaluwarsa.")
        sys.exit(1)
    except SessionRevoked:
        log.critical("[Main] STRING_SESSION telah dicabut oleh Telegram. Generate ulang dengan: cd userbot && python generate_session.py")
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("[Main] Bot dihentikan oleh pengguna.")
    except Exception as exc:
        log.exception(f"[Main] Error tidak terduga: {exc}")
        sys.exit(1)
    finally:
        log.info("[Main] IBEKS USERBOT offline.")


if __name__ == "__main__":
    main()

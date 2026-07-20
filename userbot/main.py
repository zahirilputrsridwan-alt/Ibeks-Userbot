"""
IBEKS USERBOT - Entry Point
Inisialisasi Pyrogram client, database, dan plugin loader.
"""

import sys
import os

# Tambahkan direktori userbot ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyrogram
from pyrogram import Client, filters, idle
from pyrogram.errors import ApiIdInvalid, AuthKeyUnregistered, SessionRevoked

from config import API_ID, API_HASH, STRING_SESSION, BOT_NAME, VERSION, CMD_PREFIX
from db import init_db
from loader import load_plugins
from utils.logger import log


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


def log_startup_info(client, me, plugin_stats) -> None:
    """Tampilkan informasi debug saat startup."""
    owner = me.first_name or me.username or "Unknown"
    log.info("✓ Login berhasil")
    log.info("✓ Userbot aktif")
    log.info(f"Nama akun Telegram : {owner}")
    log.info(f"User ID            : {me.id}")
    log.info(f"Prefix             : {CMD_PREFIX}")
    log.info(f"Jumlah plugin      : {len(plugin_stats['loaded'])} dimuat, {len(plugin_stats['failed'])} gagal")
    if plugin_stats['loaded']:
        log.info(f"Plugins aktif      : {', '.join(plugin_stats['loaded'])}")
    if plugin_stats['failed']:
        log.warning(f"Plugins gagal      : {', '.join(plugin_stats['failed'])}")


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

    # ── Muat semua plugin ke instance client ──────────────────────────────────
    plugin_stats = load_plugins(client)

    # ── Debug handler: log semua pesan masuk (hanya log, tidak reply) ────────
    @client.on_message(filters.incoming)
    async def debug_incoming(_client, message):
        try:
            chat_id = message.chat.id if message.chat else "n/a"
            from_id = message.from_user.id if message.from_user else "n/a"
            text = message.text or message.caption or "[no text]"
            log.info(f"[Debug] Incoming msg | chat={chat_id} from={from_id} text={text!r}")
        except Exception as exc:
            log.warning(f"[Debug] Gagal log pesan: {exc}")

    # ── Jalankan client ───────────────────────────────────────────────────────
    try:
        log.info("[Main] Menghubungkan ke Telegram...")
        client.start()

        me = client.get_me()
        log_startup_info(client, me, plugin_stats)

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

"""
IBEKS USERBOT - Entry Point
Inisialisasi Pyrogram client, database, dan plugin loader.
"""

import sys
import os

# Tambahkan direktori userbot ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyrogram import Client
from pyrogram.errors import ApiIdInvalid, AuthKeyUnregistered

from config import API_ID, API_HASH, STRING_SESSION, BOT_NAME, VERSION
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

    # ── Muat semua plugin ─────────────────────────────────────────────────────
    total = load_plugins(client)
    log.info(f"[Main] {total} plugin siap.")

    # ── Jalankan client ───────────────────────────────────────────────────────
    try:
        log.info(f"[Main] Menghubungkan ke Telegram...")
        client.run()
    except ApiIdInvalid:
        log.critical("[Main] API_ID atau API_HASH tidak valid. Periksa Replit Secrets.")
        sys.exit(1)
    except AuthKeyUnregistered:
        log.critical("[Main] STRING_SESSION tidak valid atau sudah kedaluwarsa.")
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

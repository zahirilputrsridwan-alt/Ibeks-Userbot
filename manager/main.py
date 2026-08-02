"""Entry point IBEKS MANAGER BOT."""

from __future__ import annotations

import sys

import pyrogram
from pyrogram import Client

from config import API_HASH, API_ID, BOT_NAME, BOT_TOKEN, VERSION
from database import init_db
from loader import load_plugins
from logger import install_global_error_handler, log


def validate_config() -> None:
    """Pastikan semua secret wajib tersedia sebelum bot dimulai."""
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")
    if missing:
        raise RuntimeError(f"Secret belum tersedia: {', '.join(missing)}")


def main() -> None:
    install_global_error_handler()
    validate_config()
    init_db()
    log.info("✓ Database SQLite siap.")

    client = Client(
        name="ibeks_manager_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True,
    )
    log.info(
        "%s v%s mulai dengan Pyrogram %s.",
        BOT_NAME,
        VERSION,
        pyrogram.__version__,
    )

    try:
        stats = load_plugins(client)
        if stats["failed"]:
            log.error("Sebagian plugin gagal dimuat: %s", stats["failed"])
        client.run()
    except KeyboardInterrupt:
        log.info("Manager Bot dihentikan oleh pengguna.")
    except Exception:
        log.exception("Manager Bot berhenti karena error.")
        sys.exit(1)
    finally:
        log.info("Manager Bot offline.")


if __name__ == "__main__":
    main()
"""Entry point IBEKS MANAGER BOT."""

from __future__ import annotations

import sys

import pyrogram
from pyrogram import Client, idle

from config import API_HASH, API_ID, BOT_NAME, BOT_TOKEN, VERSION
from database import init_db
from engine import (
    set_manager_bot_id,
    start_all_supervisors,
    stop_all_supervisors,
    stop_all_userbots,
)
from loader import load_plugins
from logger import install_global_error_handler, log


def validate_config() -> None:
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")
    if missing:
        raise RuntimeError(f"Secret belum tersedia: {', '.join(missing)}")
    log.info("✓ BOT_TOKEN, API_ID, dan API_HASH terbaca dari environment Secrets.")


def main() -> None:
    install_global_error_handler()
    validate_config()
    init_db()
    log.info("✓ Database berhasil dimuat.")

    client = Client(
        name="ibeks_manager_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True,
    )
    log.info("%s v%s mulai dengan Pyrogram %s.", BOT_NAME, VERSION, pyrogram.__version__)
    started = False
    try:
        client.start()
        started = True
        set_manager_bot_id(client.get_me().id)
        log.info("✓ Login berhasil.")

        stats = load_plugins(client)
        if stats["failed"]:
            log.error("Plugin gagal dimuat: %s", stats["failed"])
        required_plugins = {
            "plugins.start.start",
            "plugins.account.account",
            "plugins.admin.panel",
        }
        missing_plugins = required_plugins.difference(stats["loaded"])
        if missing_plugins:
            raise RuntimeError(
                "Plugin inti gagal dimuat: " + ", ".join(sorted(missing_plugins))
            )

        client.loop.run_until_complete(start_all_supervisors())
        log.info("✓ Bot siap menerima pesan.")
        idle()
    finally:
        if started:
            client.loop.run_until_complete(stop_all_supervisors())
            client.loop.run_until_complete(stop_all_userbots())
            client.stop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Manager Bot berhenti karena error.")
        sys.exit(1)
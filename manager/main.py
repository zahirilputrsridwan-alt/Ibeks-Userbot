"""Entry point IBEKS MANAGER BOT."""

from __future__ import annotations

import fcntl
import asyncio
import sys

import pyrogram
from pyrogram import Client, idle

from config import (
    API_HASH,
    API_ID,
    BOT_NAME,
    BOT_START_TIMEOUT_SECONDS,
    BOT_TOKEN,
    INSTANCE_LOCK_PATH,
    VERSION,
)
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


def acquire_instance_lock():
    """Pastikan hanya satu Manager Bot memakai BOT_TOKEN pada satu workspace."""
    lock_file = INSTANCE_LOCK_PATH.open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        lock_file.close()
        raise RuntimeError(
            "Manager Bot instance lain masih berjalan; startup dibatalkan."
        ) from exc
    lock_file.write(f"{__name__}\n")
    lock_file.flush()
    return lock_file


def main() -> None:
    install_global_error_handler()
    instance_lock = acquire_instance_lock()
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
        log.info("Menghubungkan Manager Bot ke Telegram...")
        try:
            start_method = getattr(client.start, "__wrapped__", None)
            start_coroutine = (
                start_method(client)
                if start_method is not None
                else client.start()
            )
            client.loop.run_until_complete(
                asyncio.wait_for(start_coroutine, timeout=BOT_START_TIMEOUT_SECONDS)
            )
        except asyncio.TimeoutError as exc:
            log.error(
                "Koneksi Telegram timeout setelah %ss; Bot belum siap menerima pesan.",
                BOT_START_TIMEOUT_SECONDS,
            )
            raise RuntimeError("Koneksi Manager Bot ke Telegram timeout.") from exc
        started = True
        bot_identity = client.get_me()
        set_manager_bot_id(bot_identity.id)
        log.info(
            "✓ Terhubung sebagai @%s (ID %s).",
            bot_identity.username or "(tanpa username)",
            bot_identity.id,
        )
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

        # Pyrogram schedules add_handler() asynchronously. Flush those tasks
        # before idle() so incoming updates cannot arrive without handlers.
        client.loop.run_until_complete(asyncio.sleep(0))
        client.loop.run_until_complete(asyncio.sleep(0))
        dispatcher_groups = client.dispatcher.groups
        handler_count = sum(len(handlers) for handlers in dispatcher_groups.values())
        log.info(
            "✓ Dispatcher aktif: %s handler dalam %s group.",
            handler_count,
            len(dispatcher_groups),
        )
        if handler_count == 0:
            raise RuntimeError("Tidak ada handler Pyrogram yang terdaftar.")

        client.loop.run_until_complete(start_all_supervisors())
        log.info("✓ Bot siap menerima pesan.")
        idle()
    finally:
        if started:
            client.loop.run_until_complete(stop_all_supervisors())
            client.loop.run_until_complete(stop_all_userbots())
            client.stop()
        fcntl.flock(instance_lock.fileno(), fcntl.LOCK_UN)
        instance_lock.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Manager Bot berhenti karena error.")
        sys.exit(1)
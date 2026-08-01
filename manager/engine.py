"""Lifecycle engine untuk proses IBEKS USERBOT per pengguna."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone

from config import USERBOT_DIR, USERBOT_MAIN, USERBOT_RUNTIME_DIR
from database import get_user, set_userbot_identity, update_userbot_state
from logger import log

ONLINE = "🟢 Online"
OFFLINE = "🔴 Offline"
STARTING = "🟡 Starting"
STOPPED = "⚪ Stopped"

_READY_TIMEOUT_SECONDS = 30
_processes: dict[int, asyncio.subprocess.Process] = {}
_watchers: dict[int, asyncio.Task] = {}
_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
_ready_events: dict[int, asyncio.Event] = {}
_ready_errors: dict[int, str] = {}
_recent_output: dict[int, list[str]] = {}
_ready_parts: dict[int, set[str]] = {}
_intentional_stops: set[int] = set()
_manager_bot_id: int = 0
_USERBOT_ID_RE = re.compile(r"User ID\s*:\s*(\d+)")
_MANAGER_HANDSHAKE = "\u2063IBEKS_USERBOT_READY\u2063"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _runtime_dir(user_id: int) -> str:
    path = USERBOT_RUNTIME_DIR / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _child_environment(user_id: int, session_string: str) -> dict[str, str]:
    """Buat environment minimal untuk child Userbot tanpa BOT_TOKEN."""
    environment = os.environ.copy()
    environment.pop("BOT_TOKEN", None)
    environment["STRING_SESSION"] = session_string
    environment["USERBOT_RUNTIME_DIR"] = _runtime_dir(user_id)
    environment["MANAGER_BOT_ID"] = str(_manager_bot_id)
    environment["MANAGER_USER_ID"] = str(user_id)
    environment["PYTHONUNBUFFERED"] = "1"
    return environment


def set_manager_bot_id(bot_id: int) -> None:
    """Simpan ID Manager Bot untuk mengizinkan relay pada child Userbot."""
    global _manager_bot_id
    _manager_bot_id = int(bot_id)


def mark_userbot_handshake(manager_user_id: int, userbot_id: int) -> None:
    """Tandai kanal privat Userbot ↔ Manager sudah terbentuk."""
    user = get_user(manager_user_id)
    if not user:
        return
    if (
        user.get("userbot_telegram_id")
        and user["userbot_telegram_id"] != userbot_id
    ):
        return
    if not user.get("userbot_telegram_id"):
        set_userbot_identity(manager_user_id, userbot_id)
    _ready_parts.setdefault(manager_user_id, set()).add("handshake")
    _maybe_mark_ready(manager_user_id)


def _maybe_mark_ready(user_id: int) -> None:
    """Set event startup setelah semua sinyal relay tersedia."""
    if _ready_parts.get(user_id) != {"login", "identity", "handshake"}:
        return
    update_userbot_state(user_id, ONLINE, last_start=_timestamp())
    event = _ready_events.get(user_id)
    if event:
        event.set()


def is_running(user_id: int) -> bool:
    process = _processes.get(user_id)
    return bool(process and process.returncode is None)


def status_for(user_id: int) -> str:
    return ONLINE if is_running(user_id) else OFFLINE


def remove_userbot_runtime(user_id: int) -> None:
    """Hapus runtime terisolasi setelah user berhasil dihapus."""
    path = USERBOT_RUNTIME_DIR / str(user_id)
    if path.exists():
        shutil.rmtree(path)


async def _watch_process(user_id: int, process: asyncio.subprocess.Process) -> None:
    try:
        if process.stdout:
            async for raw_line in process.stdout:
                line = raw_line.decode(errors="replace").rstrip()
                if line:
                    log.info("[Userbot:%s] %s", user_id, line)
                    output = _recent_output.setdefault(user_id, [])
                    output.append(line)
                    del output[:-10]
                if "✓ Login berhasil" in line or "Login berhasil" in line:
                    _ready_parts.setdefault(user_id, set()).add("login")
                    _maybe_mark_ready(user_id)
                identity = _USERBOT_ID_RE.search(line)
                if identity:
                    set_userbot_identity(user_id, int(identity.group(1)))
                    _ready_parts.setdefault(user_id, set()).add("identity")
                    _maybe_mark_ready(user_id)
                if "Error" in line or "Traceback" in line:
                    _ready_errors[user_id] = line
        await process.wait()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _ready_errors[user_id] = str(exc)
        log.exception("Watcher Userbot %s gagal", user_id)
    finally:
        if _processes.get(user_id) is process:
            _processes.pop(user_id, None)
            _watchers.pop(user_id, None)
        event = _ready_events.get(user_id)
        if event:
            event.set()
        if user_id in _intentional_stops:
            _intentional_stops.discard(user_id)
            update_userbot_state(user_id, OFFLINE, last_stop=_timestamp())
        elif process.returncode not in (None, 0):
            if user_id not in _ready_errors:
                output = _recent_output.get(user_id, [])
                if output:
                    _ready_errors[user_id] = output[-1]
            update_userbot_state(user_id, OFFLINE, last_stop=_timestamp())
            log.error(
                "Userbot %s berhenti dengan exit code %s.",
                user_id,
                process.returncode,
            )
        else:
            update_userbot_state(user_id, OFFLINE)
        _recent_output.pop(user_id, None)
        _ready_parts.pop(user_id, None)


async def start_userbot(user_id: int) -> tuple[bool, str]:
    """Mulai proses Userbot dan tunggu sampai login Pyrogram berhasil."""
    async with _locks[user_id]:
        return await _start_userbot_locked(user_id)


async def _start_userbot_locked(user_id: int) -> tuple[bool, str]:
    """Versi internal start; caller harus memegang lock user."""
    user = get_user(user_id)
    if not user or not user.get("session_string"):
        return False, "Akun Telegram belum login."
    if user.get("suspended"):
        return False, "User sedang disuspend oleh Admin."
    if is_running(user_id):
        update_userbot_state(user_id, ONLINE)
        return True, "Userbot sudah berjalan."

    update_userbot_state(user_id, STARTING)
    _ready_events[user_id] = asyncio.Event()
    _ready_parts[user_id] = set()
    _ready_errors.pop(user_id, None)
    _recent_output[user_id] = []
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            str(USERBOT_MAIN),
            cwd=str(USERBOT_DIR),
            env=_child_environment(user_id, user["session_string"]),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except Exception as exc:
        _ready_events.pop(user_id, None)
        update_userbot_state(user_id, OFFLINE)
        log.exception("Gagal memulai Userbot %s", user_id)
        return False, f"Gagal memulai Userbot: {exc}"

    _processes[user_id] = process
    _watchers[user_id] = asyncio.create_task(_watch_process(user_id, process))
    event = _ready_events[user_id]
    try:
        await asyncio.wait_for(event.wait(), timeout=_READY_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        await _terminate_process(user_id)
        _ready_events.pop(user_id, None)
        update_userbot_state(user_id, OFFLINE, last_stop=_timestamp())
        return False, "Userbot timeout saat melakukan startup."

    _ready_events.pop(user_id, None)
    if is_running(user_id) and user_id not in _ready_errors:
        update_userbot_state(user_id, ONLINE, last_start=_timestamp())
        log.info("Userbot %s berhasil online.", user_id)
        return True, "Userbot berhasil online."

    reason = _ready_errors.pop(user_id, "Proses Userbot berhenti sebelum online.")
    update_userbot_state(user_id, OFFLINE, last_stop=_timestamp())
    return False, reason


async def _terminate_process(user_id: int) -> None:
    process = _processes.get(user_id)
    if not process or process.returncode is not None:
        return
    _intentional_stops.add(user_id)
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=10)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()


async def stop_userbot(user_id: int) -> tuple[bool, str]:
    """Hentikan proses Userbot milik user."""
    async with _locks[user_id]:
        return await _stop_userbot_locked(user_id)


async def _stop_userbot_locked(user_id: int) -> tuple[bool, str]:
    """Versi internal stop; caller harus memegang lock user."""
    if not is_running(user_id):
        update_userbot_state(user_id, OFFLINE, last_stop=_timestamp())
        return True, "Userbot sudah berhenti."
    await _terminate_process(user_id)
    update_userbot_state(user_id, OFFLINE, last_stop=_timestamp())
    log.info("Userbot %s dihentikan.", user_id)
    return True, "Userbot berhasil dihentikan."


async def restart_userbot(user_id: int) -> tuple[bool, str]:
    """Hentikan lalu mulai kembali proses Userbot."""
    async with _locks[user_id]:
        if is_running(user_id):
            await _stop_userbot_locked(user_id)
        update_userbot_state(user_id, STARTING, last_restart=_timestamp())
        success, message = await _start_userbot_locked(user_id)
        if success:
            log.info("Userbot %s berhasil direstart.", user_id)
        return success, message if success else f"Restart gagal: {message}"


async def stop_all_userbots() -> None:
    """Hentikan seluruh child process saat Manager Bot shutdown."""
    for user_id in list(_processes):
        try:
            await stop_userbot(user_id)
        except Exception:
            log.exception("Gagal menghentikan Userbot %s saat shutdown.", user_id)
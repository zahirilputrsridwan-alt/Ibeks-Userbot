"""Lifecycle engine untuk proses IBEKS USERBOT per pengguna."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone

from config import (
    USERBOT_DIR,
    USERBOT_MAIN,
    USERBOT_MONITOR_INTERVAL_SECONDS,
    USERBOT_RECONNECT_INITIAL_SECONDS,
    USERBOT_RECONNECT_MAX_SECONDS,
    USERBOT_RUNTIME_DIR,
)
from database import get_user, list_logged_in_users, set_userbot_identity, update_userbot_state
from logger import log
from membership import has_active_membership

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
_manual_stops: set[int] = set()
_supervisors: dict[int, asyncio.Task] = {}
_supervisor_stop = asyncio.Event()
_manager_bot_id: int = 0
_manager_bot_username: str = ""
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
    environment["MANAGER_BOT_USERNAME"] = _manager_bot_username
    environment["MANAGER_USER_ID"] = str(user_id)
    environment["PYTHONUNBUFFERED"] = "1"
    return environment


def set_manager_bot_id(bot_id: int) -> None:
    """Simpan ID Manager Bot untuk mengizinkan relay pada child Userbot."""
    global _manager_bot_id
    _manager_bot_id = int(bot_id)


def set_manager_bot_identity(bot_id: int, username: str | None = None) -> None:
    """Simpan identitas Manager Bot untuk handshake child Userbot."""
    global _manager_bot_id, _manager_bot_username
    _manager_bot_id = int(bot_id)
    _manager_bot_username = (username or "").lstrip("@")


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


def _supervisor_is_stopping() -> bool:
    return _supervisor_stop.is_set()


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
    _manual_stops.discard(user_id)
    async with _locks[user_id]:
        return await _start_userbot_locked(user_id)


async def _ensure_stopped_for_access(user_id: int, reason: str) -> None:
    """Hentikan Userbot jika aksesnya tidak lagi valid."""
    if is_running(user_id):
        async with _locks[user_id]:
            if is_running(user_id):
                await _terminate_process(user_id)
    update_userbot_state(user_id, OFFLINE, last_stop=_timestamp())
    log.info("Userbot %s dihentikan otomatis: %s", user_id, reason)


async def _supervise_user(user_id: int) -> None:
    """Monitor satu user dan reconnect setelah crash dengan exponential backoff."""
    delay = USERBOT_RECONNECT_INITIAL_SECONDS
    while not _supervisor_is_stopping():
        if user_id in _manual_stops:
            log.info("Supervisor Userbot %s menunggu Start manual.", user_id)
            return
        user = get_user(user_id)
        if not user or not user.get("session_string"):
            return
        if user.get("suspended"):
            await _ensure_stopped_for_access(user_id, "akun disuspend")
            return
        if not has_active_membership(user):
            await _ensure_stopped_for_access(user_id, "Membership expired")
            return
        if is_running(user_id):
            delay = USERBOT_RECONNECT_INITIAL_SECONDS
            try:
                await asyncio.wait_for(
                    _supervisor_stop.wait(),
                    timeout=USERBOT_MONITOR_INTERVAL_SECONDS,
                )
            except asyncio.TimeoutError:
                continue
            return

        success, result = await start_userbot(user_id)
        if success:
            delay = USERBOT_RECONNECT_INITIAL_SECONDS
            continue
        if _supervisor_is_stopping():
            return
        log.warning(
            "Auto-reconnect Userbot %s gagal: %s. Coba lagi dalam %ss.",
            user_id,
            result,
            delay,
        )
        try:
            await asyncio.wait_for(_supervisor_stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            delay = min(delay * 2, USERBOT_RECONNECT_MAX_SECONDS)


def ensure_supervisor(user_id: int) -> None:
    """Pastikan satu supervisor saja mengelola satu user."""
    task = _supervisors.get(user_id)
    if task and not task.done():
        return
    _supervisors[user_id] = asyncio.create_task(
        _supervise_user(user_id),
        name=f"userbot-supervisor-{user_id}",
    )


def resume_supervisor(user_id: int) -> None:
    """Lanjutkan monitoring setelah akses user diaktifkan kembali."""
    _manual_stops.discard(user_id)
    ensure_supervisor(user_id)


async def start_all_supervisors() -> None:
    """Mulai monitoring untuk seluruh user yang sudah login."""
    _supervisor_stop.clear()
    for user in list_logged_in_users():
        ensure_supervisor(user["telegram_id"])
    log.info("Supervisor Userbot aktif untuk %s user.", len(_supervisors))


async def stop_supervisor(user_id: int) -> None:
    """Hentikan supervisor satu user tanpa mematikan akun lain."""
    task = _supervisors.pop(user_id, None)
    if not task:
        return
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def stop_all_supervisors() -> None:
    """Hentikan seluruh task monitoring."""
    _supervisor_stop.set()
    tasks = list(_supervisors.values())
    _supervisors.clear()
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def _start_userbot_locked(user_id: int) -> tuple[bool, str]:
    """Versi internal start; caller harus memegang lock user."""
    user = get_user(user_id)
    if not user or not user.get("session_string"):
        return False, "Akun Telegram belum login."
    if user.get("suspended"):
        return False, "User sedang disuspend oleh Admin."
    if not has_active_membership(user):
        return False, "Membership Anda telah berakhir. Silakan hubungi Admin."
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
    _manual_stops.add(user_id)
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
    _manual_stops.discard(user_id)
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
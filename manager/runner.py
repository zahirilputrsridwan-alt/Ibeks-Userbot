"""Supervisor multi-user untuk menjalankan source IBEKS USERBOT yang sama.

Manager menyimpan lifecycle setiap akun, sedangkan setiap Userbot berjalan dalam
proses Python terpisah. Proses worker memakai ``userbot/main.py`` dan loader
plugin asli sehingga tidak ada command yang diduplikasi di Manager.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from config import USERBOT_MAIN_FILE, USERBOT_RUNTIME_DIR, USERBOT_SOURCE_DIR
from database import (
    get_user,
    list_users,
    set_userbot_status,
)
from logger import log


ONLINE = "Online"
STARTING = "Starting"
OFFLINE = "Offline"
_READY_TIMEOUT = 45
_RECONCILE_INTERVAL = 5


@dataclass
class _ManagedUserbot:
    telegram_id: int
    process: subprocess.Popen
    runtime_dir: Path
    ready_file: Path
    stopping: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


class UserbotRunner:
    """Menjalankan banyak Userbot dengan session dan runtime terisolasi."""

    def __init__(self) -> None:
        self._processes: dict[int, _ManagedUserbot] = {}
        self._manual_stops: set[int] = set()
        self._lock = threading.RLock()
        self._shutdown = threading.Event()
        self._reconciler: threading.Thread | None = None

    @staticmethod
    def _eligible(user: dict | None) -> bool:
        return bool(
            user
            and user.get("session_string")
            and user.get("approval_status") == "approved"
            and user.get("status") == "Active"
        )

    def start(self) -> None:
        """Auto-start akun yang sudah approved + Active dan mulai rekonsiliasi."""
        self._shutdown.clear()
        self.reconcile_once()
        if not self._reconciler or not self._reconciler.is_alive():
            self._reconciler = threading.Thread(
                target=self._reconcile_loop,
                name="ibeks-userbot-reconciler",
                daemon=True,
            )
            self._reconciler.start()
        log.info("[Runner] Supervisor Userbot aktif.")

    def _reconcile_loop(self) -> None:
        while not self._shutdown.wait(_RECONCILE_INTERVAL):
            try:
                self.reconcile_once()
            except Exception:
                log.exception("[Runner] Rekonsiliasi Userbot gagal.")

    def reconcile_once(self) -> None:
        """Samakan proses runtime dengan status akses di SQLite."""
        users = list_users()
        users_by_id = {int(user["telegram_id"]): user for user in users}
        with self._lock:
            running_ids = list(self._processes)

        for telegram_id in running_ids:
            if not self._eligible(users_by_id.get(telegram_id)):
                self.stop_userbot(telegram_id, reason="akses tidak lagi valid")

        for user in users:
            telegram_id = int(user["telegram_id"])
            if self._eligible(user) and telegram_id not in self._manual_stops:
                self.start_userbot(telegram_id, reason="auto-start/reconcile")

    def start_userbot(self, telegram_id: int, *, reason: str = "manual") -> bool:
        """Mulai satu Userbot jika user memenuhi seluruh syarat akses."""
        user = get_user(telegram_id)
        if not self._eligible(user):
            log.info(
                "[Runner] Userbot %s tidak dijalankan: status akses tidak valid.",
                telegram_id,
            )
            return False

        self._manual_stops.discard(telegram_id)
        with self._lock:
            current = self._processes.get(telegram_id)
            if current and current.process.poll() is None:
                return True
            if current:
                self._processes.pop(telegram_id, None)

            runtime_dir = USERBOT_RUNTIME_DIR / str(telegram_id)
            runtime_dir.mkdir(parents=True, exist_ok=True)
            ready_file = runtime_dir / ".runner_ready"
            ready_file.unlink(missing_ok=True)
            environment = os.environ.copy()
            environment.update(
                {
                    "STRING_SESSION": str(user["session_string"]),
                    "IBEKS_USERBOT_RUNTIME_DIR": str(runtime_dir),
                    "IBEKS_RUNNER_READY_FILE": str(ready_file),
                    "IBEKS_MANAGER_DATABASE_PATH": str(
                        Path(__file__).resolve().parent / "database.db"
                    ),
                }
            )
            environment["PYTHONPATH"] = os.pathsep.join(
                [str(USERBOT_SOURCE_DIR), environment.get("PYTHONPATH", "")]
            ).rstrip(os.pathsep)

            set_userbot_status(telegram_id, STARTING, started=True)
            try:
                process = subprocess.Popen(
                    [sys.executable, str(USERBOT_MAIN_FILE)],
                    cwd=str(USERBOT_SOURCE_DIR),
                    env=environment,
                )
            except Exception:
                set_userbot_status(telegram_id, OFFLINE, stopped=True)
                log.exception("[Runner] Gagal memulai Userbot %s.", telegram_id)
                return False

            managed = _ManagedUserbot(
                telegram_id=telegram_id,
                process=process,
                runtime_dir=runtime_dir,
                ready_file=ready_file,
            )
            self._processes[telegram_id] = managed
            threading.Thread(
                target=self._watch_process,
                args=(managed,),
                name=f"ibeks-userbot-{telegram_id}",
                daemon=True,
            ).start()
            log.info(
                "[Runner] Userbot %s Starting (reason=%s, pid=%s).",
                telegram_id,
                reason,
                process.pid,
            )
            return True

    def _watch_process(self, managed: _ManagedUserbot) -> None:
        deadline = time.monotonic() + _READY_TIMEOUT
        while managed.process.poll() is None and time.monotonic() < deadline:
            if managed.ready_file.exists():
                set_userbot_status(managed.telegram_id, ONLINE)
                log.info("[Runner] Userbot %s Online.", managed.telegram_id)
                break
            time.sleep(0.25)

        return_code = managed.process.wait()
        with self._lock:
            is_current = self._processes.get(managed.telegram_id) is managed
            if is_current:
                self._processes.pop(managed.telegram_id, None)
        set_userbot_status(managed.telegram_id, OFFLINE, stopped=True)
        if managed.stopping:
            log.info(
                "[Runner] Userbot %s Offline setelah dihentikan (code=%s).",
                managed.telegram_id,
                return_code,
            )
        else:
            log.error(
                "[Runner] Userbot %s crash/offline (code=%s). Userbot lain tetap berjalan.",
                managed.telegram_id,
                return_code,
            )

    def stop_userbot(
        self,
        telegram_id: int,
        *,
        reason: str = "manual",
        suppress_restart: bool = False,
    ) -> bool:
        """Hentikan satu Userbot dan hapus dari daftar proses aktif."""
        if suppress_restart:
            self._manual_stops.add(telegram_id)
        with self._lock:
            managed = self._processes.pop(telegram_id, None)
        if not managed:
            user = get_user(telegram_id)
            if user and user.get("userbot_status") != OFFLINE:
                set_userbot_status(telegram_id, OFFLINE, stopped=True)
            return False

        managed.stopping = True
        managed.ready_file.unlink(missing_ok=True)
        log.info("[Runner] Menghentikan Userbot %s (reason=%s).", telegram_id, reason)
        try:
            managed.process.terminate()
            managed.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            log.warning("[Runner] Userbot %s tidak berhenti; kill dipanggil.", telegram_id)
            managed.process.kill()
            managed.process.wait(timeout=5)
        except Exception:
            log.exception("[Runner] Error saat menghentikan Userbot %s.", telegram_id)
        set_userbot_status(telegram_id, OFFLINE, stopped=True)
        return True

    def sync_user(self, telegram_id: int) -> None:
        """Segera terapkan perubahan approval/status untuk satu user."""
        user = get_user(telegram_id)
        if self._eligible(user):
            self.start_userbot(telegram_id, reason="status update")
        else:
            self._manual_stops.discard(telegram_id)
            self.stop_userbot(telegram_id, reason="status update")

    def stop_all(self) -> None:
        """Hentikan seluruh worker saat Manager shutdown."""
        self._shutdown.set()
        with self._lock:
            telegram_ids = list(self._processes)
        for telegram_id in telegram_ids:
            self.stop_userbot(telegram_id, reason="Manager shutdown")
        if self._reconciler and self._reconciler.is_alive():
            self._reconciler.join(timeout=5)
        log.info("[Runner] Semua Userbot dihentikan.")


_runner: UserbotRunner | None = None


def set_runner(runner: UserbotRunner | None) -> None:
    global _runner
    _runner = runner


def get_runner() -> UserbotRunner | None:
    return _runner
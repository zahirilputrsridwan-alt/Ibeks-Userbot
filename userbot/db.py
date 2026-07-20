"""
IBEKS USERBOT - Database Manager
Inisialisasi SQLite dan menyediakan helpers umum.
Database dibuat otomatis saat pertama kali dijalankan.
"""

import sqlite3
import threading

from config import DATABASE_PATH
from utils.logger import log

# ── Thread-local connection (aman untuk asyncio + threading) ──────────────────
_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """Kembalikan koneksi SQLite per-thread."""
    if not getattr(_local, "conn", None):
        _local.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db() -> None:
    """
    Buat semua tabel yang diperlukan jika belum ada.
    Tambahkan tabel baru di sini saat mengembangkan fitur berikutnya.
    """
    conn = get_conn()
    cursor = conn.cursor()

    # ── Tabel: users ──────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            first_name  TEXT,
            username    TEXT,
            added_at    TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Tabel: settings ───────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key     TEXT PRIMARY KEY,
            value   TEXT
        )
    """)

    # ── Tabel: logs (opsional, untuk audit sederhana) ─────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS command_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            command     TEXT,
            chat_id     INTEGER,
            executed_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    log.info("[DB] Database diinisialisasi.")


# ── Helper: settings ──────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    """Ambil nilai setting berdasarkan key."""
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    """Simpan atau perbarui setting."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()

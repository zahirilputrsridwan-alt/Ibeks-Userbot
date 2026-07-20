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


def _migrate_old_settings(cursor: sqlite3.Cursor) -> None:
    """Migrasi tabel settings dari schema lama (key, value) ke schema baru."""
    cursor.execute("PRAGMA table_info(settings)")
    columns = [row["name"] for row in cursor.fetchall()]

    if not columns or "telegram_id" in columns:
        return

    # Schema lama terdeteksi, ambil prefix jika ada lalu drop
    old_prefix = None
    if "key" in columns:
        try:
            row = cursor.execute(
                "SELECT value FROM settings WHERE key = ?", ("prefix",)
            ).fetchone()
            old_prefix = row["value"] if row else None
        except Exception as exc:
            log.warning(f"[DB] Gagal membaca prefix lama: {exc}")

    cursor.execute("DROP TABLE settings")
    cursor.execute("""
        CREATE TABLE settings (
            telegram_id  INTEGER PRIMARY KEY,
            prefix       TEXT,
            updated_at   TEXT DEFAULT (datetime('now'))
        )
    """)

    if old_prefix:
        cursor.execute(
            "INSERT INTO settings (telegram_id, prefix) VALUES (?, ?)",
            (0, old_prefix),
        )
        log.info(f"[DB] Migrasi prefix lama: {old_prefix}")


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
            telegram_id  INTEGER PRIMARY KEY,
            prefix       TEXT,
            updated_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    _migrate_old_settings(cursor)

    # ── Tabel: command_logs (audit sederhana) ─────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS command_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            command     TEXT,
            chat_id     INTEGER,
            executed_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Tabel: blacklist (broadcast) ────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            chat_id     INTEGER PRIMARY KEY,
            chat_title  TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    log.info("[DB] Database diinisialisasi.")


# ── Helper: prefix settings ───────────────────────────────────────────────────

def get_prefix(telegram_id: int, default: str = ".") -> str:
    """Ambil prefix untuk telegram_id tertentu."""
    conn = get_conn()
    row = conn.execute(
        "SELECT prefix FROM settings WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    return row["prefix"] if row and row["prefix"] else default


def set_prefix(telegram_id: int, prefix: str) -> None:
    """Simpan atau perbarui prefix untuk telegram_id tertentu."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (telegram_id, prefix, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(telegram_id) DO UPDATE SET prefix = excluded.prefix, updated_at = excluded.updated_at",
        (telegram_id, prefix),
    )
    conn.commit()


# ── Helper: blacklist ─────────────────────────────────────────────────────────

def add_blacklist(chat_id: int, chat_title: str | None = None) -> bool:
    """Tambahkan chat ke blacklist. Return True jika berhasil, False jika sudah ada."""
    conn = get_conn()
    existing = conn.execute(
        "SELECT chat_id FROM blacklist WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    if existing:
        return False
    conn.execute(
        "INSERT INTO blacklist (chat_id, chat_title) VALUES (?, ?)",
        (chat_id, chat_title or "Unknown"),
    )
    conn.commit()
    return True


def del_blacklist(chat_id: int) -> bool:
    """Hapus chat dari blacklist. Return True jika ditemukan dan dihapus."""
    conn = get_conn()
    cursor = conn.execute("DELETE FROM blacklist WHERE chat_id = ?", (chat_id,))
    conn.commit()
    return cursor.rowcount > 0


def is_blacklisted(chat_id: int) -> bool:
    """Cek apakah chat ada di blacklist."""
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM blacklist WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    return row is not None


def list_blacklist() -> list[dict]:
    """Kembalikan daftar blacklist sebagai list of dict {'chat_id', 'chat_title', 'created_at'}."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT chat_id, chat_title, created_at FROM blacklist ORDER BY created_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]

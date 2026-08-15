"""
IBEKS USERBOT - Database Manager
Inisialisasi SQLite dan menyediakan helpers umum.
Database dibuat otomatis saat pertama kali dijalankan.
"""

import sqlite3
import threading
from typing import Any

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
            auto_delete  INTEGER NOT NULL DEFAULT 1,
            delay_auto_delete INTEGER NOT NULL DEFAULT 5,
            animation    INTEGER NOT NULL DEFAULT 1,
            logger       INTEGER NOT NULL DEFAULT 1,
            emoji_mode   INTEGER NOT NULL DEFAULT 1,
            theme        TEXT NOT NULL DEFAULT 'Premium',
            language     TEXT NOT NULL DEFAULT 'id',
            timezone     TEXT NOT NULL DEFAULT 'UTC',
            pm_mode      TEXT NOT NULL DEFAULT 'all',
            pm_rejection_message TEXT NOT NULL DEFAULT '🚫 PM DITOLAK',
            tagreply_enabled INTEGER NOT NULL DEFAULT 0,
            tagreply_message TEXT NOT NULL DEFAULT 'Ada apa manggil-manggil saya? 😂',
            updated_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    _migrate_old_settings(cursor)
    _ensure_settings_columns(cursor)

    # ── Tabel: plugin_status ──────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plugin_status (
            module       TEXT PRIMARY KEY,
            filename     TEXT NOT NULL,
            category     TEXT NOT NULL,
            enabled      INTEGER NOT NULL DEFAULT 1,
            loaded       INTEGER NOT NULL DEFAULT 0,
            version      TEXT NOT NULL DEFAULT '1.0.0',
            author       TEXT NOT NULL DEFAULT 'IBEKS',
            command_count INTEGER NOT NULL DEFAULT 0,
            loaded_at    TEXT,
            file_size    INTEGER NOT NULL DEFAULT 0,
            file_path    TEXT,
            last_error   TEXT,
            updated_at   TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Tabel: themes ─────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS themes (
            name         TEXT PRIMARY KEY,
            definition   TEXT NOT NULL,
            is_active    INTEGER NOT NULL DEFAULT 0,
            updated_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    default_themes = {
        "Premium": "╭─「 {title} 」\n│\n{body}\n│\n╰─ ⨱ IBEKS USERBOT ⨱",
        "Freeze": "❄️ {title}\n\n{body}\n\n⨱ IBEKS USERBOT ⨱",
        "Minimal": "【 {title} 】\n{body}\n\n⨱ IBEKS USERBOT ⨱",
        "Neon": "╔═ {title} ═╗\n{body}\n╚═ ⨱ IBEKS USERBOT ⨱ ═╝",
        "Matrix": "┌─[ {title} ]\n│\n{body}\n│\n└─ ⨱ IBEKS USERBOT ⨱",
    }
    for theme_name, definition in default_themes.items():
        cursor.execute(
            """
            INSERT INTO themes (name, definition, is_active)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO NOTHING
            """,
            (theme_name, definition, int(theme_name == "Premium")),
        )
    cursor.execute(
        "UPDATE themes SET is_active = 0 WHERE name != "
        "(SELECT name FROM themes WHERE is_active = 1 ORDER BY name LIMIT 1)"
    )

    # ── Tabel: dashboard ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dashboard (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            runtime      TEXT,
            cpu_percent  REAL,
            ram_percent  REAL,
            disk_percent REAL,
            database_size INTEGER,
            total_plugins INTEGER,
            active_plugins INTEGER,
            inactive_plugins INTEGER,
            captured_at  TEXT DEFAULT (datetime('now'))
        )
    """)

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

    # ── Tabel: chat_lock ───────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_lock (
            chat_id     INTEGER PRIMARY KEY,
            locked      INTEGER NOT NULL DEFAULT 0,
            updated_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    log.info("[DB] Database diinisialisasi.")


def _ensure_settings_columns(cursor: sqlite3.Cursor) -> None:
    """Tambahkan kolom settings baru tanpa menghapus schema lama."""
    cursor.execute("PRAGMA table_info(settings)")
    columns = {row["name"] for row in cursor.fetchall()}
    additions = {
        "auto_delete": "INTEGER NOT NULL DEFAULT 1",
        "delay_auto_delete": "INTEGER NOT NULL DEFAULT 5",
        "animation": "INTEGER NOT NULL DEFAULT 1",
        "logger": "INTEGER NOT NULL DEFAULT 1",
        "emoji_mode": "INTEGER NOT NULL DEFAULT 1",
        "theme": "TEXT NOT NULL DEFAULT 'Premium'",
        "language": "TEXT NOT NULL DEFAULT 'id'",
        "timezone": "TEXT NOT NULL DEFAULT 'UTC'",
        "pm_mode": "TEXT NOT NULL DEFAULT 'all'",
        "pm_rejection_message": "TEXT NOT NULL DEFAULT '🚫 PM DITOLAK'",
        "tagreply_enabled": "INTEGER NOT NULL DEFAULT 0",
        "tagreply_message": "TEXT NOT NULL DEFAULT 'Ada apa manggil-manggil saya? 😂'",
    }
    for name, definition in additions.items():
        if name not in columns:
            cursor.execute(f"ALTER TABLE settings ADD COLUMN {name} {definition}")


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


DEFAULT_SETTINGS: dict[str, Any] = {
    "prefix": ".",
    "auto_delete": 1,
    "delay_auto_delete": 5,
    "animation": 1,
    "logger": 1,
    "emoji_mode": 1,
    "theme": "Premium",
    "language": "id",
    "timezone": "UTC",
    "pm_mode": "all",
    "pm_rejection_message": "🚫 PM DITOLAK",
    "tagreply_enabled": 0,
    "tagreply_message": "Ada apa manggil-manggil saya? 😂",
}


def ensure_user_settings(telegram_id: int) -> None:
    """Buat baris konfigurasi akun tanpa menimpa nilai yang sudah ada."""
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO settings
            (telegram_id, prefix, auto_delete, delay_auto_delete, animation,
             logger, emoji_mode, theme, language, timezone, pm_mode,
             pm_rejection_message, tagreply_enabled, tagreply_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(telegram_id) DO NOTHING
        """,
        (
            telegram_id,
            DEFAULT_SETTINGS["prefix"],
            DEFAULT_SETTINGS["auto_delete"],
            DEFAULT_SETTINGS["delay_auto_delete"],
            DEFAULT_SETTINGS["animation"],
            DEFAULT_SETTINGS["logger"],
            DEFAULT_SETTINGS["emoji_mode"],
            DEFAULT_SETTINGS["theme"],
            DEFAULT_SETTINGS["language"],
            DEFAULT_SETTINGS["timezone"],
            DEFAULT_SETTINGS["pm_mode"],
            DEFAULT_SETTINGS["pm_rejection_message"],
            DEFAULT_SETTINGS["tagreply_enabled"],
            DEFAULT_SETTINGS["tagreply_message"],
        ),
    )
    conn.commit()


def get_setting(telegram_id: int, key: str, default: Any = None) -> Any:
    """Ambil satu setting akun secara aman."""
    if key not in DEFAULT_SETTINGS:
        raise ValueError(f"Setting tidak dikenal: {key}")
    ensure_user_settings(telegram_id)
    row = get_conn().execute(
        f"SELECT {key} FROM settings WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    return row[key] if row and row[key] is not None else (
        DEFAULT_SETTINGS[key] if default is None else default
    )


def set_setting(telegram_id: int, key: str, value: Any) -> None:
    """Simpan setting akun tanpa memengaruhi kolom konfigurasi lain."""
    if key not in DEFAULT_SETTINGS:
        raise ValueError(f"Setting tidak dikenal: {key}")
    ensure_user_settings(telegram_id)
    conn = get_conn()
    conn.execute(
        f"UPDATE settings SET {key} = ?, updated_at = datetime('now') "
        "WHERE telegram_id = ?",
        (value, telegram_id),
    )
    conn.commit()


def list_plugin_status() -> list[dict]:
    """Kembalikan seluruh status plugin untuk Control Panel."""
    rows = get_conn().execute(
        "SELECT * FROM plugin_status ORDER BY category, filename"
    ).fetchall()
    return [dict(row) for row in rows]


def get_plugin_status(module: str) -> dict | None:
    row = get_conn().execute(
        "SELECT * FROM plugin_status WHERE module = ?", (module,)
    ).fetchone()
    return dict(row) if row else None


def upsert_plugin_status(metadata: dict) -> None:
    """Daftarkan metadata plugin sambil mempertahankan enabled pilihan user."""
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO plugin_status
            (module, filename, category, version, author, command_count,
             file_size, file_path, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(module) DO UPDATE SET
            filename = excluded.filename,
            category = excluded.category,
            version = excluded.version,
            author = excluded.author,
            command_count = excluded.command_count,
            file_size = excluded.file_size,
            file_path = excluded.file_path,
            updated_at = excluded.updated_at
        """,
        (
            metadata["module"],
            metadata["filename"],
            metadata["category"],
            metadata.get("version", "1.0.0"),
            metadata.get("author", "IBEKS"),
            metadata.get("command_count", 0),
            metadata.get("file_size", 0),
            metadata.get("file_path"),
        ),
    )
    conn.commit()


def set_plugin_runtime(
    module: str,
    *,
    loaded: bool,
    loaded_at: str | None = None,
    last_error: str | None = None,
) -> None:
    conn = get_conn()
    conn.execute(
        """
        UPDATE plugin_status
        SET loaded = ?, loaded_at = ?, last_error = ?, updated_at = datetime('now')
        WHERE module = ?
        """,
        (int(loaded), loaded_at, last_error, module),
    )
    conn.commit()


def set_plugin_enabled(module: str, enabled: bool) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE plugin_status SET enabled = ?, updated_at = datetime('now') WHERE module = ?",
        (int(enabled), module),
    )
    conn.commit()


def active_theme() -> str:
    row = get_conn().execute(
        "SELECT name FROM themes WHERE is_active = 1 ORDER BY name LIMIT 1"
    ).fetchone()
    return row["name"] if row else "Premium"


def save_theme(name: str, definition: str, active: bool = False) -> None:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO themes (name, definition, is_active, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(name) DO UPDATE SET
            definition = excluded.definition,
            is_active = excluded.is_active,
            updated_at = excluded.updated_at
        """,
        (name, definition, int(active)),
    )
    if active:
        conn.execute(
            "UPDATE themes SET is_active = 0 WHERE name != ?", (name,)
        )
    conn.commit()


def list_themes() -> list[dict]:
    rows = get_conn().execute(
        "SELECT name, definition, is_active, updated_at FROM themes ORDER BY name"
    ).fetchall()
    return [dict(row) for row in rows]


def record_dashboard(snapshot: dict) -> None:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO dashboard
            (runtime, cpu_percent, ram_percent, disk_percent, database_size,
             total_plugins, active_plugins, inactive_plugins)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot.get("runtime"),
            snapshot.get("cpu_percent"),
            snapshot.get("ram_percent"),
            snapshot.get("disk_percent"),
            snapshot.get("database_size"),
            snapshot.get("total_plugins"),
            snapshot.get("active_plugins"),
            snapshot.get("inactive_plugins"),
        ),
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


# ── Helper: chat lock ─────────────────────────────────────────────────────────

def set_chat_lock(chat_id: int, locked: bool) -> None:
    """Simpan status lock untuk chat tertentu."""
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO chat_lock (chat_id, locked, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(chat_id) DO UPDATE SET
            locked = excluded.locked,
            updated_at = excluded.updated_at
        """,
        (chat_id, int(bool(locked))),
    )
    conn.commit()


def is_chat_locked(chat_id: int) -> bool:
    """Kembalikan True bila chat memiliki status lock aktif."""
    conn = get_conn()
    row = conn.execute(
        "SELECT locked FROM chat_lock WHERE chat_id = ?",
        (chat_id,),
    ).fetchone()
    return bool(row and row["locked"])

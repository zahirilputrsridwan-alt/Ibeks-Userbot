"""SQLite storage for the IBEKS Userbot.

The userbot keeps one SQLite database for settings and runtime state.  All
helpers in this module are synchronous because each operation is a small
SQLite transaction and the callers already run in the Pyrogram event loop.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DATABASE_PATH


_SETTINGS_COLUMNS = {
    "prefix",
    "auto_delete",
    "delay_auto_delete",
    "animation",
    "logger",
    "emoji_mode",
    "theme",
    "language",
    "timezone",
    "pm_mode",
    "pm_rejection_message",
    "tagreply_enabled",
    "tagreply_message",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    """Open the configured database with dictionary-like rows."""
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    """Create/migrate the existing userbot schema without replacing its data."""
    conn = get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                added_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS settings (
                telegram_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT '.',
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS chat_lock (
                chat_id INTEGER PRIMARY KEY,
                locked INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT (datetime('now')),
                source TEXT NOT NULL DEFAULT 'manual'
            );
            CREATE TABLE IF NOT EXISTS blacklist (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS command_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                command TEXT,
                chat_id INTEGER,
                executed_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS plugin_status (
                module TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                category TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                loaded INTEGER NOT NULL DEFAULT 0,
                version TEXT NOT NULL DEFAULT '1.0.0',
                author TEXT NOT NULL DEFAULT 'IBEKS',
                command_count INTEGER NOT NULL DEFAULT 0,
                loaded_at TEXT,
                file_size INTEGER NOT NULL DEFAULT 0,
                file_path TEXT,
                last_error TEXT,
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS dashboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                runtime TEXT,
                cpu_percent REAL,
                ram_percent REAL,
                disk_percent REAL,
                database_size INTEGER,
                total_plugins INTEGER,
                active_plugins INTEGER,
                inactive_plugins INTEGER,
                captured_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS themes (
                name TEXT PRIMARY KEY,
                definition TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT (datetime('now'))
            );
            """
        )

        # Settings were added incrementally by the control-panel features.
        for column, definition in (
            ("auto_delete", "INTEGER NOT NULL DEFAULT 1"),
            ("delay_auto_delete", "INTEGER NOT NULL DEFAULT 5"),
            ("animation", "INTEGER NOT NULL DEFAULT 1"),
            ("logger", "INTEGER NOT NULL DEFAULT 1"),
            ("emoji_mode", "INTEGER NOT NULL DEFAULT 1"),
            ("theme", "TEXT NOT NULL DEFAULT 'Premium'"),
            ("language", "TEXT NOT NULL DEFAULT 'id'"),
            ("timezone", "TEXT NOT NULL DEFAULT 'UTC'"),
            ("pm_mode", "TEXT NOT NULL DEFAULT 'all'"),
            ("pm_rejection_message", "TEXT NOT NULL DEFAULT '🚫 PM DITOLAK'"),
            ("tagreply_enabled", "INTEGER NOT NULL DEFAULT 0"),
            ("tagreply_message", "TEXT NOT NULL DEFAULT 'Ada apa manggil-manggil saya? 😂'"),
        ):
            _ensure_column(conn, "settings", column, definition)

        # Keep manual chat locks and PM-control locks distinguishable while
        # retaining the existing chat_lock table and existing rows.
        _ensure_column(conn, "chat_lock", "source", "TEXT NOT NULL DEFAULT 'manual'")

        default_definition = "╭─「 {title} 」\n│\n{body}\n│\n╰─ ⨱ IBEKS USERBOT ⨱"
        for name in ("Premium", "Freeze", "Minimal", "Neon", "Matrix"):
            conn.execute(
                """
                INSERT OR IGNORE INTO themes
                    (name, definition, is_active, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, default_definition, 1 if name == "Premium" else 0, _now()),
            )
        conn.commit()
    finally:
        conn.close()


def ensure_user_settings(telegram_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO settings (telegram_id, prefix, updated_at) VALUES (?, '.', ?)",
            (int(telegram_id), _now()),
        )
        conn.commit()
    finally:
        conn.close()


def get_setting(telegram_id: int, key: str, default: Any = None) -> Any:
    if key not in _SETTINGS_COLUMNS:
        raise ValueError(f"Unknown settings key: {key}")
    ensure_user_settings(int(telegram_id))
    conn = get_conn()
    try:
        row = conn.execute(
            f"SELECT {key} FROM settings WHERE telegram_id = ?",
            (int(telegram_id),),
        ).fetchone()
        return row[key] if row is not None else default
    finally:
        conn.close()


def set_setting(telegram_id: int, key: str, value: Any) -> None:
    if key not in _SETTINGS_COLUMNS:
        raise ValueError(f"Unknown settings key: {key}")
    ensure_user_settings(int(telegram_id))
    conn = get_conn()
    try:
        conn.execute(
            f"UPDATE settings SET {key} = ?, updated_at = ? WHERE telegram_id = ?",
            (value, _now(), int(telegram_id)),
        )
        conn.commit()
    finally:
        conn.close()


def get_prefix(telegram_id: int, default: str = ".") -> str:
    return str(get_setting(telegram_id, "prefix", default) or default)


def set_prefix(telegram_id: int, prefix: str) -> None:
    set_setting(telegram_id, "prefix", prefix)


def set_chat_lock(chat_id: int, locked: bool, source: str = "manual") -> None:
    """Set a lock in the existing chat_lock table.

    ``source='pm_control'`` is retained to identify legacy PM-control locks.
    It lets explicit ``.pm all``/``.pm contacts`` cleanup avoid touching chats
    manually locked by the owner; the current PM gate never creates new locks.
    """
    source = str(source or "manual")
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO chat_lock (chat_id, locked, updated_at, source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                locked = excluded.locked,
                updated_at = excluded.updated_at,
                source = excluded.source
            """,
            (int(chat_id), int(bool(locked)), _now(), source),
        )
        conn.commit()
    finally:
        conn.close()


def is_chat_locked(chat_id: int) -> bool:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT locked FROM chat_lock WHERE chat_id = ?",
            (int(chat_id),),
        ).fetchone()
        return bool(row and row["locked"])
    finally:
        conn.close()


def list_locked_chats(source: str | None = None) -> list[int]:
    """Return active locks, optionally restricted to one lock owner/source."""
    conn = get_conn()
    try:
        if source is None:
            rows = conn.execute(
                "SELECT chat_id FROM chat_lock WHERE locked = 1"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT chat_id FROM chat_lock WHERE locked = 1 AND source = ?",
                (str(source),),
            ).fetchall()
        return [int(row["chat_id"]) for row in rows]
    finally:
        conn.close()


def add_blacklist(chat_id: int, chat_title: str = "") -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO blacklist (chat_id, chat_title, created_at) VALUES (?, ?, ?)",
            (int(chat_id), chat_title, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def del_blacklist(chat_id: int) -> bool:
    conn = get_conn()
    try:
        cursor = conn.execute("DELETE FROM blacklist WHERE chat_id = ?", (int(chat_id),))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def is_blacklisted(chat_id: int) -> bool:
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT 1 FROM blacklist WHERE chat_id = ?", (int(chat_id),)
        ).fetchone() is not None
    finally:
        conn.close()


def list_blacklist() -> list[dict]:
    conn = get_conn()
    try:
        return [dict(row) for row in conn.execute(
            "SELECT chat_id, chat_title, created_at FROM blacklist ORDER BY created_at DESC"
        ).fetchall()]
    finally:
        conn.close()


def upsert_plugin_status(metadata: dict) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO plugin_status
                (module, filename, category, version, author, command_count,
                 file_size, file_path, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                int(metadata.get("command_count", 0)),
                int(metadata.get("file_size", 0)),
                metadata.get("file_path"),
                _now(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_plugin_status(module_name: str) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM plugin_status WHERE module = ?", (module_name,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_plugin_status() -> list[dict]:
    conn = get_conn()
    try:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM plugin_status ORDER BY module"
        ).fetchall()]
    finally:
        conn.close()


def set_plugin_runtime(module_name: str, loaded: bool, loaded_at: str | None = None,
                       last_error: str | None = None) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE plugin_status
            SET loaded = ?, loaded_at = ?, last_error = ?, updated_at = ?
            WHERE module = ?
            """,
            (int(bool(loaded)), loaded_at, last_error, _now(), module_name),
        )
        conn.commit()
    finally:
        conn.close()


def set_plugin_enabled(module_name: str, enabled: bool) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE plugin_status SET enabled = ?, updated_at = ? WHERE module = ?",
            (int(bool(enabled)), _now(), module_name),
        )
        conn.commit()
    finally:
        conn.close()


def record_dashboard(snapshot: dict) -> None:
    conn = get_conn()
    try:
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
    finally:
        conn.close()


def list_themes() -> list[dict]:
    conn = get_conn()
    try:
        return [dict(row) for row in conn.execute(
            "SELECT name, definition, is_active, updated_at FROM themes ORDER BY name"
        ).fetchall()]
    finally:
        conn.close()


def active_theme() -> str:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT name FROM themes WHERE is_active = 1 ORDER BY name LIMIT 1"
        ).fetchone()
        return str(row["name"]) if row else "Premium"
    finally:
        conn.close()


def save_theme(name: str, definition: str, active: bool = False) -> None:
    conn = get_conn()
    try:
        if active:
            conn.execute("UPDATE themes SET is_active = 0, updated_at = ?", (_now(),))
        conn.execute(
            """
            INSERT INTO themes (name, definition, is_active, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                definition = excluded.definition,
                is_active = excluded.is_active,
                updated_at = excluded.updated_at
            """,
            (name, definition, int(bool(active)), _now()),
        )
        conn.commit()
    finally:
        conn.close()

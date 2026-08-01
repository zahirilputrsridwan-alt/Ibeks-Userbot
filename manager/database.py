"""SQLite storage untuk data pengguna Manager Bot."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import DATABASE_PATH


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(Path(DATABASE_PATH))
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Buat database dan tabel users bila belum tersedia."""
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Belum Aktif',
                phone_number TEXT,
                session_string TEXT,
                login_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        for column, definition in {
            "phone_number": "TEXT",
            "session_string": "TEXT",
            "login_at": "TEXT",
        }.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
        connection.commit()


def get_user(telegram_id: int) -> dict | None:
    """Ambil satu user berdasarkan Telegram ID."""
    with _connect() as connection:
        row = connection.execute(
            "SELECT telegram_id, username, full_name, status, phone_number, "
            "session_string, login_at, created_at, updated_at "
            "FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
    return dict(row) if row else None


def get_or_create_user(
    telegram_id: int,
    username: str | None,
    full_name: str,
) -> dict:
    """Ambil user atau buat record awal dengan status Belum Aktif."""
    existing = get_user(telegram_id)
    if existing:
        with _connect() as connection:
            connection.execute(
                "UPDATE users SET username = ?, full_name = ?, updated_at = ? "
                "WHERE telegram_id = ?",
                (username, full_name, _now(), telegram_id),
            )
            connection.commit()
        return get_user(telegram_id) or existing

    timestamp = _now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO users
                (telegram_id, username, full_name, status, created_at, updated_at)
            VALUES (?, ?, ?, 'Belum Aktif', ?, ?)
            """,
            (telegram_id, username, full_name, timestamp, timestamp),
        )
        connection.commit()
    return get_user(telegram_id) or {}


def save_login(
    telegram_id: int,
    phone_number: str,
    session_string: str,
    username: str | None,
    full_name: str,
) -> None:
    """Simpan hasil login tanpa pernah mengembalikan session ke pengguna."""
    timestamp = _now()
    with _connect() as connection:
        connection.execute(
            """
            UPDATE users
            SET username = ?,
                full_name = ?,
                phone_number = ?,
                session_string = ?,
                login_at = ?,
                status = 'Aktif',
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                username,
                full_name,
                phone_number,
                session_string,
                timestamp,
                timestamp,
                telegram_id,
            ),
        )
        connection.commit()

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
                userbot_telegram_id INTEGER,
                login_at TEXT,
                userbot_status TEXT NOT NULL DEFAULT '🔴 Offline',
                last_start TEXT,
                last_stop TEXT,
                last_restart TEXT,
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
            "userbot_telegram_id": "INTEGER",
            "login_at": "TEXT",
            "userbot_status": "TEXT NOT NULL DEFAULT '🔴 Offline'",
            "last_start": "TEXT",
            "last_stop": "TEXT",
            "last_restart": "TEXT",
        }.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
        connection.commit()


def get_user(telegram_id: int) -> dict | None:
    """Ambil satu user berdasarkan Telegram ID."""
    with _connect() as connection:
        row = connection.execute(
            "SELECT telegram_id, username, full_name, status, phone_number, "
            "session_string, userbot_telegram_id, login_at, userbot_status, last_start, last_stop, "
            "last_restart, created_at, updated_at "
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


def get_user_by_userbot_id(userbot_telegram_id: int) -> dict | None:
    """Ambil pemilik Manager berdasarkan ID akun Telegram Userbot."""
    with _connect() as connection:
        row = connection.execute(
            "SELECT telegram_id, username, full_name, status, phone_number, "
            "session_string, userbot_telegram_id, login_at, userbot_status, "
            "last_start, last_stop, last_restart, created_at, updated_at "
            "FROM users WHERE userbot_telegram_id = ?",
            (userbot_telegram_id,),
        ).fetchone()
    return dict(row) if row else None


def set_userbot_identity(telegram_id: int, userbot_telegram_id: int) -> None:
    """Simpan ID akun Userbot setelah child berhasil login."""
    with _connect() as connection:
        connection.execute(
            "UPDATE users SET userbot_telegram_id = ?, updated_at = ? "
            "WHERE telegram_id = ?",
            (userbot_telegram_id, _now(), telegram_id),
        )
        connection.commit()


def save_login(
    telegram_id: int,
    phone_number: str,
    session_string: str,
    userbot_telegram_id: int,
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
                userbot_telegram_id = ?,
                login_at = ?,
                status = 'Aktif',
                userbot_status = '🟡 Starting',
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                username,
                full_name,
                phone_number,
                session_string,
                userbot_telegram_id,
                timestamp,
                timestamp,
                telegram_id,
            ),
        )
        connection.commit()


def update_userbot_state(
    telegram_id: int,
    status: str,
    *,
    last_start: str | None = None,
    last_stop: str | None = None,
    last_restart: str | None = None,
) -> None:
    """Simpan status dan timestamp lifecycle Userbot."""
    fields = ["userbot_status = ?", "updated_at = ?"]
    values: list[str | int | None] = [status, _now()]
    for column, value in (
        ("last_start", last_start),
        ("last_stop", last_stop),
        ("last_restart", last_restart),
    ):
        if value is not None:
            fields.append(f"{column} = ?")
            values.append(value)
    values.append(telegram_id)
    with _connect() as connection:
        connection.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE telegram_id = ?",
            values,
        )
        connection.commit()

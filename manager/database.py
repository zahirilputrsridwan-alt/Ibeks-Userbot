"""Akses SQLite untuk data dasar pengguna Manager Bot."""

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
    """Buat database dan tabel users sesuai kontrak project."""
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Belum Aktif',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def get_user(telegram_id: int) -> dict | None:
    """Ambil satu pengguna berdasarkan Telegram ID."""
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT telegram_id, username, full_name, status, created_at, updated_at
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        ).fetchone()
    return dict(row) if row else None


def get_or_create_user(
    telegram_id: int,
    username: str | None,
    full_name: str,
) -> dict:
    """Buat user pertama kali atau segarkan profilnya."""
    timestamp = _now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO users (
                telegram_id, username, full_name, status, created_at, updated_at
            )
            VALUES (?, ?, ?, 'Belum Aktif', ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                updated_at = excluded.updated_at
            """,
            (
                telegram_id,
                username,
                full_name or "Pengguna Telegram",
                timestamp,
                timestamp,
            ),
        )
        connection.commit()
    return get_user(telegram_id) or {}
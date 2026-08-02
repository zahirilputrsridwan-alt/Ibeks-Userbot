"""Akses SQLite untuk pengguna dan hasil login Telegram."""

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
    """Buat tabel users dan migrasikan kolom login tanpa menghapus data lama."""
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
                updated_at TEXT NOT NULL,
                phone_number TEXT,
                session_string TEXT,
                login_at TEXT,
                approval_status TEXT NOT NULL DEFAULT 'pending',
                approved_by INTEGER,
                approved_at TEXT
            )
            """
        )
        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        for column, definition in (
            ("phone_number", "TEXT"),
            ("session_string", "TEXT"),
            ("login_at", "TEXT"),
            ("approval_status", "TEXT NOT NULL DEFAULT 'pending'"),
            ("approved_by", "INTEGER"),
            ("approved_at", "TEXT"),
        ):
            if column not in existing_columns:
                connection.execute(
                    f"ALTER TABLE users ADD COLUMN {column} {definition}"
                )
        connection.commit()


def get_user(telegram_id: int) -> dict | None:
    """Ambil satu pengguna berdasarkan Telegram ID."""
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT telegram_id, username, full_name, status, created_at, updated_at,
                   phone_number, session_string, login_at, approval_status,
                   approved_by, approved_at
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


def mark_login_pending(telegram_id: int, phone_number: str) -> None:
    """Tandai percobaan login aktif tanpa menyimpan OTP atau password."""
    timestamp = _now()
    with _connect() as connection:
        connection.execute(
            """
            UPDATE users
            SET phone_number = ?,
                status = 'Pending',
                session_string = NULL,
                login_at = NULL,
                approval_status = 'pending',
                approved_by = NULL,
                approved_at = NULL,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (phone_number, timestamp, telegram_id),
        )
        connection.commit()


def save_login_success(
    telegram_id: int,
    phone_number: str,
    session_string: str,
    *,
    approval_status: str = "pending",
    approved_by: int | None = None,
) -> None:
    """Simpan session hanya setelah akun Telegram berhasil login."""
    timestamp = _now()
    approved_at = timestamp if approval_status == "approved" else None
    with _connect() as connection:
        connection.execute(
            """
            UPDATE users
            SET phone_number = ?,
                session_string = ?,
                login_at = ?,
                status = 'Active',
                approval_status = ?,
                approved_by = ?,
                approved_at = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                phone_number,
                session_string,
                timestamp,
                approval_status,
                approved_by,
                approved_at,
                timestamp,
                telegram_id,
            ),
        )
        connection.commit()


def mark_login_failed(telegram_id: int) -> None:
    """Kembalikan status ke Pending setelah percobaan login gagal."""
    timestamp = _now()
    with _connect() as connection:
        connection.execute(
            """
            UPDATE users
            SET status = 'Pending', updated_at = ?
            WHERE telegram_id = ?
            """,
            (timestamp, telegram_id),
        )
        connection.commit()


def approve_user(telegram_id: int, owner_id: int) -> dict | None:
    """Setujui user yang masih menunggu persetujuan."""
    timestamp = _now()
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE users
            SET approval_status = 'approved',
                approved_by = ?,
                approved_at = ?,
                updated_at = ?
            WHERE telegram_id = ? AND approval_status = 'pending'
            """,
            (owner_id, timestamp, timestamp, telegram_id),
        )
        connection.commit()
        if cursor.rowcount != 1:
            return None
    return get_user(telegram_id)


def reject_user(telegram_id: int) -> dict | None:
    """Tolak user dan hapus session Telegram yang tersimpan."""
    timestamp = _now()
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE users
            SET approval_status = 'rejected',
                session_string = NULL,
                updated_at = ?
            WHERE telegram_id = ? AND approval_status = 'pending'
            """,
            (timestamp, telegram_id),
        )
        connection.commit()
        if cursor.rowcount != 1:
            return None
    return get_user(telegram_id)
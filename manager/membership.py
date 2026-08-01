"""Aturan Membership Manager Bot."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from database import get_user, set_membership_expired_at

MEMBERSHIP_DAYS = 30
MEMBERSHIP_ACTIVE = "Active"
MEMBERSHIP_EXPIRED = "Expired"


def utc_now() -> datetime:
    """Ambil waktu sekarang dalam UTC."""
    return datetime.now(timezone.utc)


def _parse_expired_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def membership_status(
    expired_at: str | None,
    *,
    now: datetime | None = None,
) -> str:
    """Kembalikan Active atau Expired dari waktu expired."""
    expiry = _parse_expired_at(expired_at)
    current = now or utc_now()
    if expiry and expiry > current:
        return MEMBERSHIP_ACTIVE
    return MEMBERSHIP_EXPIRED


def membership_days_remaining(
    expired_at: str | None,
    *,
    now: datetime | None = None,
) -> int:
    """Hitung sisa hari kalender ke atas; Membership habis bernilai nol."""
    expiry = _parse_expired_at(expired_at)
    current = now or utc_now()
    if not expiry or expiry <= current:
        return 0
    return max(0, math.ceil((expiry - current).total_seconds() / 86400))


def membership_info(
    user: dict,
    *,
    now: datetime | None = None,
) -> dict[str, str | int | None]:
    """Buat data tampilan Membership dari record user."""
    expired_at = user.get("membership_expired_at")
    return {
        "status": membership_status(expired_at, now=now),
        "expired_at": expired_at,
        "days_remaining": membership_days_remaining(expired_at, now=now),
    }


def has_active_membership(
    user: dict,
    *,
    now: datetime | None = None,
) -> bool:
    """Cek apakah user boleh memakai Terminal Userbot."""
    return membership_status(
        user.get("membership_expired_at"),
        now=now,
    ) == MEMBERSHIP_ACTIVE


def ensure_login_membership(telegram_id: int) -> str:
    """Beri 30 hari pada login pertama yang belum memiliki Membership."""
    user = get_user(telegram_id)
    if not user:
        raise ValueError("User belum terdaftar.")
    if user.get("membership_expired_at"):
        return user["membership_expired_at"]

    expired_at = utc_now() + timedelta(days=MEMBERSHIP_DAYS)
    value = expired_at.isoformat(timespec="seconds")
    set_membership_expired_at(telegram_id, value)
    return value


def extend_membership(telegram_id: int, days: int) -> str:
    """Perpanjang Membership; fungsi ini siap dipakai plugin Admin."""
    if days <= 0:
        raise ValueError("Jumlah hari harus lebih besar dari nol.")

    user = get_user(telegram_id)
    if not user:
        raise ValueError("User belum terdaftar.")

    current = utc_now()
    existing = _parse_expired_at(user.get("membership_expired_at"))
    base = existing if existing and existing > current else current
    expired_at = base + timedelta(days=days)
    value = expired_at.isoformat(timespec="seconds")
    set_membership_expired_at(telegram_id, value)
    return value
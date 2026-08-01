"""Operasi dan aturan Panel Admin Manager Bot."""

from __future__ import annotations

from config import OWNER_ID
from database import (
    delete_user,
    get_user,
    list_users,
    log_admin_activity,
    set_suspended,
    statistics,
)
from membership import extend_membership


def is_owner(telegram_id: int) -> bool:
    """Cek apakah Telegram ID memiliki akses Owner."""
    return int(telegram_id) == OWNER_ID


def _audit(admin_id: int, action: str, target: int | None = None, details: str = "") -> None:
    log_admin_activity(admin_id, action, target, details or None)


def admin_users(admin_id: int) -> list[dict]:
    _require_owner(admin_id)
    _audit(admin_id, "list_users")
    return list_users()


def admin_user_detail(admin_id: int, user_id: int) -> dict | None:
    _require_owner(admin_id)
    user = get_user(user_id)
    _audit(admin_id, "user_detail", user_id, "found" if user else "not_found")
    return user


def admin_extend(admin_id: int, user_id: int, days: int) -> str:
    _require_owner(admin_id)
    expired_at = extend_membership(user_id, days)
    _audit(admin_id, "extend_membership", user_id, f"days={days}")
    return expired_at


def admin_suspend(admin_id: int, user_id: int) -> bool:
    _require_owner(admin_id)
    changed = set_suspended(user_id, True)
    _audit(admin_id, "suspend_user", user_id, "success" if changed else "not_found")
    return changed


def admin_activate(admin_id: int, user_id: int) -> bool:
    _require_owner(admin_id)
    changed = set_suspended(user_id, False)
    _audit(admin_id, "activate_user", user_id, "success" if changed else "not_found")
    return changed


def admin_delete(admin_id: int, user_id: int) -> bool:
    _require_owner(admin_id)
    deleted = delete_user(user_id)
    _audit(admin_id, "delete_user", user_id, "success" if deleted else "not_found")
    return deleted


def admin_statistics(admin_id: int) -> dict[str, int]:
    _require_owner(admin_id)
    result = statistics()
    _audit(admin_id, "statistics")
    return result


def _require_owner(telegram_id: int) -> None:
    if not is_owner(telegram_id):
        log_admin_activity(telegram_id, "access_denied")
        raise PermissionError("Akses Admin ditolak.")
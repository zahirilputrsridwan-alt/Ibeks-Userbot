"""Konfigurasi mandiri IBEKS MANAGER BOT."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PLUGINS_DIR = BASE_DIR / "plugins"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"
DATABASE_PATH = BASE_DIR / "database.db"
INSTANCE_LOCK_PATH = BASE_DIR / "manager.lock"

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
API_ID = int(os.environ.get("API_ID", "0") or 0)
API_HASH = os.environ.get("API_HASH", "").strip()
OWNER_ID = int(os.environ.get("OWNER_ID", "0") or 0)

BOT_NAME = "IBEKS MANAGER BOT"
VERSION = "1.0.0"
DEVELOPER = "IBEKS Developer"

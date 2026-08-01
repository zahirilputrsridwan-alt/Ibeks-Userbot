"""Konfigurasi IBEKS MANAGER BOT dari Replit Secrets."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PLUGINS_DIR = BASE_DIR / "plugins"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"
DATABASE_PATH = BASE_DIR / "database.db"
USERBOT_DIR = BASE_DIR.parent / "userbot"
USERBOT_MAIN = USERBOT_DIR / "main.py"
USERBOT_RUNTIME_DIR = BASE_DIR / "userbot_runtime"

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_ID = int(os.environ.get("API_ID", "0") or 0)
API_HASH = os.environ.get("API_HASH", "")
BOT_NAME = "IBEKS MANAGER BOT"
VERSION = "1.0.0"
LOGIN_TIMEOUT_SECONDS = 300
OWNER_ID = 8823165964
USERBOT_MONITOR_INTERVAL_SECONDS = 15
USERBOT_RECONNECT_INITIAL_SECONDS = 5
USERBOT_RECONNECT_MAX_SECONDS = 300
INSTANCE_LOCK_PATH = BASE_DIR / "manager.lock"
BOT_START_TIMEOUT_SECONDS = 45

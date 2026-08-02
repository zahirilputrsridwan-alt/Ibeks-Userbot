"""
IBEKS USERBOT - Configuration
Membaca semua konfigurasi dari environment variables (Replit Secrets).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram credentials ──────────────────────────────────────────────────────
API_ID: int = int(os.environ.get("API_ID", 0))
API_HASH: str = os.environ.get("API_HASH", "")
STRING_SESSION: str = os.environ.get("STRING_SESSION", "")
OWNER_ID: int = int(os.environ.get("OWNER_ID", 0) or 0)

# ── Bot metadata ──────────────────────────────────────────────────────────────
BOT_NAME: str = "IBEKS USERBOT"
VERSION: str = "1.0.0"
CMD_PREFIX: str = "."  # Default fallback; prefix aktif dibaca dari database

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
MANAGER_DATABASE_PATH: str = os.path.join(
    BASE_DIR, "..", "manager", "database.db"
)
PLUGINS_DIR: str = os.path.join(BASE_DIR, "plugins")
DATABASE_PATH: str = os.path.join(BASE_DIR, "database.db")
LOGS_DIR: str = os.path.join(BASE_DIR, "logs")
MAIN_FILE: str = os.path.join(BASE_DIR, "main.py")

# ── Restart state ─────────────────────────────────────────────────────────────
RESTART_STATE_FILE: str = os.path.join(BASE_DIR, ".restart_state")

# ── Auto-delete delay (detik) ─────────────────────────────────────────────────
AUTO_DELETE_CMD: int = 5   # Hapus pesan command setelah N detik

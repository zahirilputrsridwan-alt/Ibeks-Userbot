"""
IBEKS USERBOT - Plugin Loader
Memuat semua plugin dalam folder plugins/ secara otomatis.
Tidak ada import manual yang diperlukan.
"""

import importlib
import os
import sys

from utils.logger import log
from config import PLUGINS_DIR


def load_plugins(client) -> int:
    """
    Scan seluruh subdirektori dalam PLUGINS_DIR dan muat setiap file .py
    sebagai modul Pyrogram. Kembalikan jumlah plugin yang berhasil dimuat.

    Parameters
    ----------
    client : pyrogram.Client
        Instance Pyrogram yang akan digunakan plugin untuk mendaftar handler.
    """
    loaded = 0
    failed = 0

    # Tambahkan direktori userbot ke sys.path agar import relatif berjalan
    userbot_dir = os.path.dirname(os.path.abspath(__file__))
    if userbot_dir not in sys.path:
        sys.path.insert(0, userbot_dir)

    for root, dirs, files in os.walk(PLUGINS_DIR):
        # Lewati folder __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for filename in sorted(files):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue

            filepath = os.path.join(root, filename)

            # Buat nama modul relatif dari PLUGINS_DIR
            rel_path = os.path.relpath(filepath, userbot_dir)
            module_name = rel_path.replace(os.sep, ".").removesuffix(".py")

            try:
                module = importlib.import_module(module_name)

                # Daftarkan handler ke client jika modul menyediakan fungsi setup()
                if hasattr(module, "setup"):
                    module.setup(client)

                log.info(f"[Loader] ✓ Plugin dimuat: {module_name}")
                loaded += 1
            except Exception as exc:
                log.error(f"[Loader] ✗ Gagal memuat plugin {module_name}: {exc}")
                failed += 1

    log.info(f"[Loader] Total plugin: {loaded} berhasil, {failed} gagal.")
    return loaded

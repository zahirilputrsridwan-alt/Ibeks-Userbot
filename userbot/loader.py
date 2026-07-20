"""
IBEKS USERBOT - Plugin Loader
Memuat semua plugin dalam folder plugins/ secara otomatis.
Tidak ada import manual yang diperlukan.

Setiap plugin dapat mendaftarkan handler ke instance client dengan cara
menyediakan fungsi `setup(client)` yang berisi decorator `@client.on_message(...)`.
"""

import importlib
import os
import sys
import traceback

from utils.logger import log
from config import PLUGINS_DIR


def load_plugins(client) -> dict:
    """
    Scan seluruh subdirektori dalam PLUGINS_DIR, import setiap file .py,
    lalu panggil `setup(client)` jika tersedia.

    Parameters
    ----------
    client : pyrogram.Client
        Instance client Pyrogram yang aktif.

    Returns
    -------
    dict
        {'loaded': list nama modul berhasil, 'failed': list nama modul gagal}
    """
    loaded = []
    failed = []

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

                # Panggil setup(client) jika plugin menyediakannya
                if hasattr(module, "setup") and callable(getattr(module, "setup")):
                    module.setup(client)
                    log.info(f"[Loader] ✓ Plugin aktif: {module_name}")
                else:
                    log.warning(f"[Loader] ⚠ Plugin {module_name} tidak memiliki fungsi setup(); dilewati.")

                loaded.append(module_name)
            except Exception as exc:
                err = traceback.format_exc()
                log.error(f"[Loader] ✗ Gagal memuat plugin {module_name}: {exc}\n{err}")
                failed.append(module_name)

    log.info(f"[Loader] Total plugin: {len(loaded)} berhasil, {len(failed)} gagal.")
    if failed:
        log.warning(f"[Loader] Plugin gagal: {failed}")

    return {"loaded": loaded, "failed": failed}

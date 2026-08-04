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


_PLUGIN_STATS = {
    "loaded": [],
    "failed": [],
    "failed_details": [],
}


def plugin_filename(module_name: str) -> str:
    """Ubah nama modul menjadi nama file plugin untuk ditampilkan."""
    return f"{module_name.rsplit('.', 1)[-1]}.py"


def plugin_category(module_name: str) -> str:
    """Kembalikan kategori folder plugin dengan nama tampilan yang konsisten."""
    parts = module_name.split(".")
    category = parts[-2] if len(parts) > 1 else "other"
    return {
        "admin": "Permission",
        "ai": "AI",
        "broadcast": "Broadcast",
        "core": "Core",
        "fun": "Fun",
        "permission": "Permission",
        "utility": "Utility",
        "voice": "Voice",
    }.get(category, category.replace("_", " ").title())


def get_plugin_stats() -> dict:
    """Ambil salinan statistik plugin terakhir yang dimuat."""
    return {
        "loaded": list(_PLUGIN_STATS["loaded"]),
        "failed": list(_PLUGIN_STATS["failed"]),
        "failed_details": [dict(item) for item in _PLUGIN_STATS["failed_details"]],
    }


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
    failed_details = []

    # Tambahkan direktori userbot ke sys.path agar import relatif berjalan
    userbot_dir = os.path.dirname(os.path.abspath(__file__))
    if userbot_dir not in sys.path:
        sys.path.insert(0, userbot_dir)

    for root, dirs, files in os.walk(PLUGINS_DIR):
        # Hanya folder kategori command yang dipindai.
        dirs[:] = [d for d in dirs if d not in {"__pycache__", "utils"}]

        for filename in sorted(files):
            if (
                not filename.endswith(".py")
                or filename.startswith("_")
                or filename == "__init__.py"
            ):
                continue

            filepath = os.path.join(root, filename)

            # Buat nama modul relatif dari PLUGINS_DIR
            rel_path = os.path.relpath(filepath, userbot_dir)
            module_name = rel_path.replace(os.sep, ".").removesuffix(".py")

            try:
                module = importlib.import_module(module_name)

                # Panggil setup(client) jika plugin menyediakannya
                setup = getattr(module, "setup", None)
                if not callable(setup):
                    raise TypeError("Plugin tidak memiliki fungsi setup(client)")

                setup(client)
                log.info(f"[Loader] ✓ Plugin aktif: {module_name}")

                loaded.append(module_name)
            except Exception as exc:
                err = traceback.format_exc()
                log.error(f"[Loader] ✗ Gagal memuat plugin {module_name}: {exc}\n{err}")
                failed.append(module_name)
                failed_details.append(
                    {
                        "module": module_name,
                        "filename": plugin_filename(module_name),
                        "category": plugin_category(module_name),
                        "error_type": type(exc).__name__,
                        "reason": str(exc).strip() or type(exc).__name__,
                    }
                )

    log.info(f"[Loader] Total plugin: {len(loaded)} berhasil, {len(failed)} gagal.")
    if failed:
        log.warning(f"[Loader] Plugin gagal: {failed}")

    _PLUGIN_STATS["loaded"] = loaded
    _PLUGIN_STATS["failed"] = failed
    _PLUGIN_STATS["failed_details"] = failed_details
    return get_plugin_stats()

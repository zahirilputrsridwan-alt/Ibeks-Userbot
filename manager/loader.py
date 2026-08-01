"""Plugin loader otomatis untuk seluruh folder manager/plugins."""

from __future__ import annotations

import importlib
import sys
import traceback

from config import PLUGINS_DIR
from logger import log


def load_plugins(client) -> dict:
    """Import semua file plugin dan panggil setup(client)."""
    loaded: list[str] = []
    failed: list[dict] = []
    root = PLUGINS_DIR.resolve()
    package_root = root.parent

    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(package_root)
        if path.name == "__init__.py" or "__pycache__" in relative.parts:
            continue
        module_name = ".".join(relative.with_suffix("").parts)
        try:
            module = importlib.import_module(module_name)
            setup = getattr(module, "setup", None)
            if not callable(setup):
                raise TypeError("Plugin tidak memiliki fungsi setup(client)")
            setup(client)
            loaded.append(module_name)
            log.info("Plugin aktif: %s", module_name)
        except Exception as exc:
            log.error("Plugin gagal dimuat %s: %s\n%s", module_name, exc, traceback.format_exc())
            failed.append({"module": module_name, "error": str(exc)})

    log.info("Total plugin: %s berhasil, %s gagal.", len(loaded), len(failed))
    return {"loaded": loaded, "failed": failed}

"""
IBEKS Control Panel Tahap 1.

Command baru:
  .panel
  .plugin [list|info|enable|disable|reload|reloadall]
  .theme [list|set|preview]
  .dashboard / .stats
  .settings [key value]

Plugin ini sengaja berdiri sendiri. Plugin lama tetap menggunakan loader dan
decorator yang sama, sedangkan semua UI baru melewati Theme Engine.
"""

from __future__ import annotations

import asyncio
import os
import platform
import shutil
import sys
import time
from datetime import datetime

import psutil
import pyrogram
from pyrogram import filters
from pyrogram.errors import MessageNotModified
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup

from config import AUTO_DELETE_CMD, DATABASE_PATH, VERSION
from db import (
    ensure_user_settings,
    get_conn,
    get_plugin_status,
    get_setting,
    list_plugin_status,
    record_dashboard,
    set_plugin_enabled,
    set_setting,
)
from loader import (
    disable_plugin,
    enable_plugin,
    get_plugin_stats,
    plugin_modules,
    reload_plugin,
)
from plugins.utils.ui import edit_ui, send_ui
from utils.autodelete import auto_delete
from utils.control_log import record as audit
from utils.control_ui import body, keyboard, nav_rows
from utils.filters import dynamic_command
from utils.logger import log
from utils.theme import available, current, emoji, render, render_theme, set_active


_STARTED_AT = time.monotonic()
_BOOL_SETTINGS = {
    "auto_delete": "Auto Delete",
    "animation": "Animation",
    "logger": "Logger",
    "emoji_mode": "Emoji Mode",
}
_SETTING_LABELS = {
    **_BOOL_SETTINGS,
    "delay_auto_delete": "Delay Auto Delete",
    "prefix": "Prefix",
    "theme": "Theme",
    "language": "Language",
    "timezone": "Timezone",
}
_SETTING_ALIASES = {
    "autodelete": "auto_delete",
    "delay": "delay_auto_delete",
    "emoji": "emoji_mode",
}


def _owner_id(message) -> int:
    return int(getattr(getattr(message, "from_user", None), "id", 0) or 0)


def _args(message) -> list[str]:
    text = (message.text or message.caption or "").strip()
    return text.split()[1:]


def _plugin_matches(query: str) -> list[dict]:
    needle = query.casefold().removesuffix(".py")
    rows = list_plugin_status()
    return [
        row for row in rows
        if row["module"].casefold() == needle
        or row["filename"].casefold().removesuffix(".py") == needle
        or row["module"].rsplit(".", 1)[-1].casefold() == needle
    ]


def _plugin_row(query: str) -> dict | None:
    matches = _plugin_matches(query)
    return matches[0] if len(matches) == 1 else None


def _status_label(row: dict) -> str:
    return "Aktif" if row["enabled"] and row["loaded"] else "Nonaktif"


def _plugin_counts(rows: list[dict]) -> tuple[int, int, int]:
    total = len(rows)
    active = sum(1 for row in rows if row["enabled"] and row["loaded"])
    return total, active, total - active


def _center_panel_markup() -> InlineKeyboardMarkup:
    """Keyboard utama IBEKS Control Center untuk command .panel."""
    return keyboard(
        [
            [("📦 Plugin", "cc:plugins"), ("🎨 Theme", "cc:themes")],
            [("📊 Dashboard", "cc:dashboard"), ("⚙️ Settings", "cc:settings")],
            [("⚡ Macro", "cc:macro"), ("👤 Permission", "cc:permission")],
            [("☁️ Backup", "cc:backup"), ("🔄 Update", "cc:update")],
            [("❌ Close", "cc:close")],
        ]
    )


def _panel_markup() -> InlineKeyboardMarkup:
    """Keyboard legacy untuk command panel internal cp:* lainnya."""
    return keyboard(
        [
            [("📦 Plugin Manager", "cp:plugins"), ("🎨 Theme Engine", "cp:themes")],
            [("📊 Dashboard", "cp:dashboard"), ("⚙️ Settings", "cp:settings")],
            *nav_rows("cp:home"),
        ]
    )


def _center_nav(back: str = "cc:home") -> list[list[tuple[str, str]]]:
    return [[
        ("⬅ Back", back),
        ("🏠 Home", "cc:home"),
        ("❌ Close", "cc:close"),
    ]]


def _center_text(title: str, lines: list[str]) -> str:
    """Render Control Center melalui Theme Engine yang sudah ada."""
    return render(title, "\n".join(lines))


def _center_owner_id(message_or_query) -> int:
    user = getattr(message_or_query, "from_user", None)
    if not user:
        user = getattr(getattr(message_or_query, "message", None), "from_user", None)
    return int(getattr(user, "id", 0) or 0)


def _center_launcher_text() -> str:
    """Teks minimal launcher .panel; detail hanya ada di submenu."""
    return "💎 𝗜𝗕𝗘𝗞𝗦 𝗖𝗢𝗡𝗧𝗥𝗢𝗟\n\nSilakan pilih menu di bawah."


def _plugin_center_markup():
    return keyboard(
        [
            [("📋 Daftar Plugin", "cc:plugins:list")],
            [("➕ Enable", "cc:plugins:enable"), ("➖ Disable", "cc:plugins:disable")],
            [("🔄 Reload", "cc:plugins:reload")],
            *_center_nav(),
        ]
    )


def _plugin_action_markup(action: str):
    rows = [
        [
            (
                f"{'✅' if row['enabled'] and row['loaded'] else '⛔'} "
                f"{row['module'].rsplit('.', 1)[-1]}",
                f"cc:plugin:{action}:{row['module']}",
            )
        ]
        for row in list_plugin_status()
    ]
    return keyboard(rows + _center_nav("cc:plugins"))


def _theme_center_markup():
    names = ("Premium", "Freeze", "Minimal", "Neon", "Matrix")
    return keyboard(
        [[(f"{'✅ ' if name == current() else ''}{name}", f"cc:theme:set:{name}")]
         for name in names] + _center_nav()
    )


def _settings_center_markup(owner: int):
    return keyboard(
        [
            [(f"🗑 Auto Delete: {'ON' if get_setting(owner, 'auto_delete') else 'OFF'}",
              "cc:setting:auto_delete")],
            [(f"✨ Animation: {'ON' if get_setting(owner, 'animation') else 'OFF'}",
              "cc:setting:animation")],
            [(f"😀 Emoji: {'ON' if get_setting(owner, 'emoji_mode') else 'OFF'}",
              "cc:setting:emoji_mode")],
            [(f"⌨ Prefix: {get_setting(owner, 'prefix', '.')}", "cc:setting:prefix")],
            [(f"🌐 Language: {get_setting(owner, 'language', 'id')}", "cc:setting:language")],
            [("🎨 Theme", "cc:themes")],
            *_center_nav(),
        ]
    )


def _dashboard_center_lines() -> list[str]:
    data = _dashboard_snapshot()
    return [
        f"⏱ Runtime\n│  ╰➤ {data['runtime']}",
        f"🖥 CPU\n│  ╰➤ {data['cpu_percent']:.1f}%",
        f"🧠 RAM\n│  ╰➤ {data['ram_percent']:.1f}%",
        f"🗄 Database\n│  ╰➤ {data['database_size'] / 1024:.2f} KB",
        f"📦 Plugin\n│  ╰➤ {data['active_plugins']} aktif / {data['total_plugins']} total",
        f"🐍 Python\n│  ╰➤ {platform.python_version()}",
        f"⚙️ Pyrogram\n│  ╰➤ {pyrogram.__version__}",
    ]


def _center_info_lines(page: str) -> list[str]:
    details = {
        "macro": [
            "⚡ Macro",
            "",
            "Macro Center siap digunakan.",
            "Tidak ada konfigurasi macro yang diubah.",
        ],
        "permission": [
            "👤 Permission",
            "",
            "Mode akses: Owner Userbot",
            "Command tetap dibatasi oleh filters.me.",
        ],
        "backup": [
            "☁️ Backup",
            "",
            "Backup Center siap digunakan.",
            "Data dan session tidak diubah dari panel ini.",
        ],
        "update": [
            "🔄 Update",
            "",
            f"Versi saat ini: {VERSION}",
            "Update plugin dilakukan melalui loader yang sudah ada.",
        ],
    }
    return details[page]


async def _center_edit(query, text: str, markup):
    try:
        await edit_ui(query._client, query.message, text, reply_markup=markup)
    except MessageNotModified:
        pass
    except Exception as exc:
        log.warning("[ControlCenter] Gagal mengedit panel: %s", exc)


async def _center_show_home(query):
    await _center_edit(
        query,
        _center_launcher_text(),
        _center_panel_markup(),
    )


async def _center_show_plugins(query):
    rows = list_plugin_status()
    total, active, inactive = _plugin_counts(rows)
    await _center_edit(
        query,
        _center_text(
            "📦 𝗣𝗟𝗨𝗚𝗜𝗡",
            [
                f"Total Plugin\n│  ╰➤ {total}",
                f"Plugin Aktif\n│  ╰➤ {active}",
                f"Plugin Nonaktif\n│  ╰➤ {inactive}",
            ],
        ),
        _plugin_center_markup(),
    )


async def _center_show_plugin_list(query):
    rows = list_plugin_status()
    lines = [
        f"Total Plugin\n│  ╰➤ {len(rows)}",
        "",
        *[
            f"{'✅' if row['enabled'] and row['loaded'] else '⛔'} "
            f"{row['module']} — {_status_label(row)}"
            for row in rows
        ],
    ]
    await _center_edit(query, _center_text("📋 𝗗𝗔𝗙𝗧𝗔𝗥 𝗣𝗟𝗨𝗚𝗜𝗡", lines), keyboard(_center_nav("cc:plugins")))


async def _center_show_plugin_action(query, action: str):
    label = {"enable": "Enable", "disable": "Disable", "reload": "Reload"}[action]
    await _center_edit(
        query,
        _center_text(
            f"{'➕' if action == 'enable' else '➖' if action == 'disable' else '🔄'} {label.upper()}",
            ["Pilih plugin yang ingin diproses."],
        ),
        _plugin_action_markup(action),
    )


async def _center_show_themes(query):
    await _center_edit(
        query,
        _center_text(
            "🎨 𝗧𝗛𝗘𝗠𝗘",
            [f"Tema Aktif\n│  ╰➤ {current()}"],
        ),
        _theme_center_markup(),
    )


async def _center_show_dashboard(query):
    await _center_edit(query, _center_text("📊 𝗗𝗔𝗦𝗛𝗕𝗢𝗔𝗥𝗗", _dashboard_center_lines()), keyboard(_center_nav()))


async def _center_show_settings(query):
    owner = _center_owner_id(query)
    ensure_user_settings(owner)
    await _center_edit(
        query,
        _center_text(
            "⚙️ 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦",
            [
                f"🗑 Auto Delete\n│  ╰➤ {'Aktif' if get_setting(owner, 'auto_delete') else 'Nonaktif'}",
                f"✨ Animation\n│  ╰➤ {'Aktif' if get_setting(owner, 'animation') else 'Nonaktif'}",
                f"😀 Emoji\n│  ╰➤ {'Aktif' if get_setting(owner, 'emoji_mode') else 'Nonaktif'}",
                f"⌨ Prefix\n│  ╰➤ {get_setting(owner, 'prefix', '.')}",
                f"🌐 Language\n│  ╰➤ {get_setting(owner, 'language', 'id')}",
                f"🎨 Theme\n│  ╰➤ {current()}",
            ],
        ),
        _settings_center_markup(owner),
    )


async def _center_show_info(query, page: str):
    title = {
        "macro": "⚡ 𝗠𝗔𝗖𝗥𝗢",
        "permission": "👤 𝗣𝗘𝗥𝗠𝗜𝗦𝗦𝗜𝗢𝗡",
        "backup": "☁️ 𝗕𝗔𝗖𝗞𝗨𝗣",
        "update": "🔄 𝗨𝗣𝗗𝗔𝗧𝗘",
    }[page]
    await _center_edit(query, _center_text(title, _center_info_lines(page)), keyboard(_center_nav()))


async def _center_callback_handler(query: CallbackQuery):
    data = query.data or ""
    await query.answer()
    if data == "cc:close":
        try:
            await query.message.delete()
        except Exception:
            pass
    elif data == "cc:home":
        await _center_show_home(query)
    elif data == "cc:plugins":
        await _center_show_plugins(query)
    elif data == "cc:plugins:list":
        await _center_show_plugin_list(query)
    elif data.startswith("cc:plugins:"):
        await _center_show_plugin_action(query, data.removeprefix("cc:plugins:"))
    elif data.startswith("cc:plugin:"):
        _, _, action, module = data.split(":", 3)
        row = get_plugin_status(module)
        result = "Plugin tidak ditemukan."
        if row and not (module == __name__ and action == "disable"):
            if action == "enable":
                result = "Plugin berhasil diaktifkan." if enable_plugin(module) else "Plugin gagal diaktifkan."
                if result.startswith("Plugin berhasil"):
                    ok, detail = reload_plugin(query._client, module)
                    if not ok:
                        result = f"Plugin diaktifkan, tetapi reload gagal: {detail}"
            elif action == "disable":
                result = "Plugin berhasil dinonaktifkan." if disable_plugin(query._client, module) else "Plugin gagal dinonaktifkan."
            elif action == "reload":
                ok, detail = reload_plugin(query._client, module)
                result = detail if ok else f"Reload gagal: {detail}"
            audit(f"{action.title()} Plugin", f"{module} user={query.from_user.id}")
        elif module == __name__ and action == "disable":
            result = "Control Panel tidak dapat dinonaktifkan dari dirinya sendiri."
        await _center_edit(
            query,
            _center_text("📦 𝗣𝗟𝗨𝗚𝗜𝗡", [f"├ {result}"]),
            _plugin_center_markup(),
        )
    elif data == "cc:themes":
        await _center_show_themes(query)
    elif data.startswith("cc:theme:set:"):
        name = data.removeprefix("cc:theme:set:")
        if set_active(name):
            audit("Ganti Theme", f"theme={name} user={query.from_user.id}")
        await _center_show_themes(query)
    elif data == "cc:dashboard":
        await _center_show_dashboard(query)
    elif data == "cc:settings":
        await _center_show_settings(query)
    elif data.startswith("cc:setting:"):
        key = data.removeprefix("cc:setting:")
        owner = _center_owner_id(query)
        if key in _BOOL_SETTINGS:
            set_setting(owner, key, int(not bool(get_setting(owner, key))))
        elif key == "prefix":
            prefixes = [".", "/", "!", "?"]
            old = str(get_setting(owner, key, "."))
            set_setting(owner, key, prefixes[(prefixes.index(old) + 1) % len(prefixes)] if old in prefixes else ".")
        elif key == "language":
            old = str(get_setting(owner, key, "id"))
            set_setting(owner, key, "en" if old == "id" else "id")
        await _center_show_settings(query)
    elif data in {"cc:macro", "cc:permission", "cc:backup", "cc:update"}:
        await _center_show_info(query, data.removeprefix("cc:"))


def _plugin_markup():
    return keyboard(
        [
            [("📋 Semua Plugin", "cp:plugins:list")],
            *nav_rows(),
        ]
    )


def _theme_markup():
    return keyboard(
        [
            [("📋 Daftar Tema", "cp:themes:list")],
            *nav_rows(),
        ]
    )


def _settings_markup(owner_id: int):
    values = {
        key: get_setting(owner_id, key)
        for key in _BOOL_SETTINGS
    }
    return keyboard(
        [
            [
                (f"Auto Delete: {'ON' if values['auto_delete'] else 'OFF'}", "cp:setting:auto_delete"),
                (f"Animation: {'ON' if values['animation'] else 'OFF'}", "cp:setting:animation"),
            ],
            [
                (f"Logger: {'ON' if values['logger'] else 'OFF'}", "cp:setting:logger"),
                (f"Emoji: {'ON' if values['emoji_mode'] else 'OFF'}", "cp:setting:emoji_mode"),
            ],
            [("⏱ Delay +1", "cp:setting:delay_up"), ("⏱ Delay -1", "cp:setting:delay_down")],
            [("📝 Prefix", "cp:setting:prefix"), ("🌐 Language", "cp:setting:language")],
            [("🎨 Theme", "cp:themes"), ("🌍 Timezone", "cp:setting:timezone")],
            *nav_rows(),
        ]
    )


def _settings_lines(owner_id: int) -> list[str]:
    lines = []
    for key, label in _SETTING_LABELS.items():
        value = get_setting(owner_id, key)
        if key in _BOOL_SETTINGS:
            value = "Aktif" if value else "Nonaktif"
        lines.append(f"├ {label}\n│  ╰➤ {value}")
    return lines


def _plugin_lines(rows: list[dict]) -> list[str]:
    total, active, inactive = _plugin_counts(rows)
    lines = [
        f"├ Total Plugin\n│  ╰➤ {total}",
        f"├ Plugin Aktif\n│  ╰➤ {active}",
        f"├ Plugin Nonaktif\n│  ╰➤ {inactive}",
        "│",
    ]
    for row in rows:
        lines.append(
            f"{'✅' if row['enabled'] and row['loaded'] else '⛔'} "
            f"{row['module']} — {_status_label(row)}"
        )
    return lines


def _plugin_info_lines(row: dict) -> list[str]:
    loaded_at = row["loaded_at"] or "-"
    size_kb = row["file_size"] / 1024 if row["file_size"] else 0
    return [
        f"├ Nama Plugin\n│  ╰➤ {row['module']}",
        f"├ Versi\n│  ╰➤ {row['version']}",
        f"├ Author\n│  ╰➤ {row['author']}",
        f"├ Jumlah Command\n│  ╰➤ {row['command_count']}",
        f"├ Status\n│  ╰➤ {_status_label(row)}",
        f"├ Tanggal Dimuat\n│  ╰➤ {loaded_at}",
        f"├ Ukuran File\n│  ╰➤ {size_kb:.2f} KB",
        f"├ File\n│  ╰➤ {row['filename']}",
    ]


def _dashboard_snapshot() -> dict:
    rows = list_plugin_status()
    total, active, inactive = _plugin_counts(rows)
    database_size = os.path.getsize(DATABASE_PATH) if os.path.exists(DATABASE_PATH) else 0
    disk = shutil.disk_usage(os.path.dirname(DATABASE_PATH) or ".")
    snapshot = {
        "runtime": _runtime_text(),
        "cpu_percent": psutil.cpu_percent(interval=0.05),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": (disk.used / disk.total * 100) if disk.total else 0,
        "database_size": database_size,
        "total_plugins": total,
        "active_plugins": active,
        "inactive_plugins": inactive,
    }
    record_dashboard(snapshot)
    return snapshot


def _runtime_text() -> str:
    elapsed = int(time.monotonic() - _STARTED_AT)
    days, remainder = divmod(elapsed, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours:02d}h {minutes:02d}m {seconds:02d}s"


def _dashboard_lines() -> list[str]:
    data = _dashboard_snapshot()
    return [
        f"├ Runtime\n│  ╰➤ {data['runtime']}",
        f"├ CPU\n│  ╰➤ {data['cpu_percent']:.1f}%",
        f"├ RAM\n│  ╰➤ {data['ram_percent']:.1f}%",
        f"├ Disk Usage\n│  ╰➤ {data['disk_percent']:.1f}%",
        f"├ Ukuran Database\n│  ╰➤ {data['database_size'] / 1024:.2f} KB",
        f"├ Plugin Aktif\n│  ╰➤ {data['active_plugins']}",
        f"├ Plugin Nonaktif\n│  ╰➤ {data['inactive_plugins']}",
        f"├ Total Plugin\n│  ╰➤ {data['total_plugins']}",
        f"├ Versi Userbot\n│  ╰➤ {VERSION}",
        f"├ Versi Python\n│  ╰➤ {platform.python_version()}",
        f"├ Versi Pyrogram\n│  ╰➤ {pyrogram.__version__}",
    ]


async def _edit(query: CallbackQuery, title: str, lines: list[str], markup=None):
    try:
        await query._client.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.id,
            text=render(f"{emoji(title)} {title}", "\n".join(lines)),
            reply_markup=markup,
        )
    except MessageNotModified:
        pass
    except Exception as exc:
        log.warning("[ControlPanel] Gagal mengedit panel: %s", exc)


async def _show_home(query):
    await _edit(
        query,
        "IBEKS CONTROL PANEL",
        ["├ Pilih menu untuk mengelola Userbot.", "├ Semua konfigurasi tersimpan di SQLite."],
        _panel_markup(),
    )


async def _show_plugins(query, detail: str | None = None):
    if detail:
        row = _plugin_row(detail)
        if not row:
            await _edit(query, "PLUGIN INFO", ["├ Plugin tidak ditemukan atau nama ambigu."], _plugin_markup())
            return
        await _edit(query, "PLUGIN INFO", _plugin_info_lines(row), keyboard(nav_rows("cp:plugins:list")))
        return
    await _edit(query, "PLUGIN MANAGER", ["├ Kelola status plugin dan lifecycle handler."], _plugin_markup())


async def _show_plugin_list(query):
    rows = list_plugin_status()
    markup_rows = [
        [(f"{'✅' if row['enabled'] and row['loaded'] else '⛔'} {row['module'].rsplit('.', 1)[-1]}", f"cp:plugin:info:{row['module']}")]
        for row in rows
    ]
    await _edit(
        query,
        "DAFTAR PLUGIN",
        _plugin_lines(rows),
        keyboard(markup_rows + nav_rows("cp:plugins")),
    )


async def _show_themes(query):
    active = current()
    lines = [
        f"├ Tema Aktif\n│  ╰➤ {active}",
        "│",
    ]
    for item in available():
        lines.append(f"{'✅' if item['name'] == active else '▫️'} {item['name']}")
    await _edit(query, "THEME ENGINE", lines, _theme_markup())


async def _show_theme_list(query):
    lines = [f"├ Tema Aktif\n│  ╰➤ {current()}", "│"]
    lines.extend(
        f"{'✅' if item['name'] == current() else '▫️'} {item['name']}"
        for item in available()
    )
    theme_rows = [
        [(f"{'✅' if item['name'] == current() else '▫️'} {item['name']}", f"cp:theme:set:{item['name']}")]
        for item in available()
    ]
    await _edit(query, "DAFTAR TEMA", lines, keyboard(theme_rows + nav_rows("cp:themes")))


async def _show_settings(query):
    owner = int(query.from_user.id)
    ensure_user_settings(owner)
    await _edit(query, "SETTINGS", _settings_lines(owner), _settings_markup(owner))


async def _show_dashboard(query):
    await _edit(query, "DASHBOARD", _dashboard_lines(), keyboard(nav_rows()))


async def _callback_handler(client, query: CallbackQuery):
    data = query.data or ""
    await query.answer()
    if data == "cp:close":
        try:
            await query.message.delete()
        except Exception:
            pass
        return
    if data == "cp:home":
        await _show_home(query)
    elif data == "cp:plugins":
        await _show_plugins(query)
    elif data == "cp:plugins:list":
        await _show_plugin_list(query)
    elif data.startswith("cp:plugin:info:"):
        await _show_plugins(query, data.removeprefix("cp:plugin:info:"))
    elif data == "cp:themes":
        await _show_themes(query)
    elif data == "cp:themes:list":
        await _show_theme_list(query)
    elif data == "cp:dashboard":
        await _show_dashboard(query)
    elif data == "cp:settings":
        await _show_settings(query)
    elif data.startswith("cp:setting:"):
        key = data.removeprefix("cp:setting:")
        owner = int(query.from_user.id)
        if key in _BOOL_SETTINGS:
            value = not bool(get_setting(owner, key))
            set_setting(owner, key, int(value))
            audit("Perubahan Settings", f"{key}={int(value)} user={owner}")
        elif key in {"delay_up", "delay_down"}:
            old = int(get_setting(owner, "delay_auto_delete"))
            delta = 1 if key == "delay_up" else -1
            set_setting(owner, "delay_auto_delete", max(0, min(3600, old + delta)))
            audit("Perubahan Settings", f"delay_auto_delete={old + delta} user={owner}")
        elif key == "prefix":
            prefixes = [".", "/", "!", "?"]
            old = str(get_setting(owner, "prefix"))
            new = prefixes[(prefixes.index(old) + 1) % len(prefixes)] if old in prefixes else "."
            set_setting(owner, "prefix", new)
            audit("Perubahan Settings", f"prefix={new} user={owner}")
        elif key == "language":
            languages = ["id", "en"]
            old = str(get_setting(owner, "language"))
            new = languages[(languages.index(old) + 1) % len(languages)] if old in languages else "id"
            set_setting(owner, "language", new)
            audit("Perubahan Settings", f"language={new} user={owner}")
        elif key == "timezone":
            timezones = ["UTC", "Asia/Jakarta", "Asia/Singapore"]
            old = str(get_setting(owner, "timezone"))
            new = timezones[(timezones.index(old) + 1) % len(timezones)] if old in timezones else "UTC"
            set_setting(owner, "timezone", new)
            audit("Perubahan Settings", f"timezone={new} user={owner}")
        else:
            await query.answer(f"Gunakan command .settings {key} <nilai>", show_alert=True)
        await _show_settings(query)
    elif data.startswith("cp:theme:set:"):
        name = data.removeprefix("cp:theme:set:")
        if set_active(name):
            audit("Ganti Theme", f"theme={name} user={query.from_user.id}")
        await _show_themes(query)


def _command_result(title: str, lines: list[str]) -> str:
    return render(f"{emoji(title)} {title}", "\n".join(lines))


async def _send_command_panel(client, message, title: str, lines: list[str], markup=None):
    # reply_markup dibuat eksplisit agar InlineKeyboardMarkup tidak hilang
    # ketika helper UI meneruskan argumen ke Pyrogram.
    await client.send_message(
        chat_id=message.chat.id,
        text=_command_result(title, lines),
        reply_markup=markup,
    )


def _settings_command(owner: int, args: list[str]) -> tuple[bool, str]:
    if len(args) < 2:
        return False, "Format: `.settings <nama> <nilai>`"
    key = _SETTING_ALIASES.get(args[0].casefold(), args[0].casefold())
    if key not in _SETTING_LABELS:
        return False, f"Setting tidak dikenal: {args[0]}"
    value = " ".join(args[1:]).strip()
    if key in _BOOL_SETTINGS:
        normalized = value.casefold()
        if normalized not in {"on", "off", "1", "0", "true", "false"}:
            return False, f"Nilai {key} harus on/off."
        value = int(normalized in {"on", "1", "true"})
    elif key == "delay_auto_delete":
        try:
            value = max(0, min(3600, int(value)))
        except ValueError:
            return False, "Delay harus berupa angka 0-3600."
    elif key == "prefix" and value not in {".", "/", "!", "?"}:
        return False, "Prefix yang diizinkan: ., /, !, ?"
    set_setting(owner, key, value)
    audit("Perubahan Settings", f"{key}={value} user={owner}")
    return True, f"{_SETTING_LABELS[key]} diubah menjadi `{value}`."


def setup(client):
    @client.on_message(dynamic_command("panel") & filters.me)
    async def cmd_panel(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        await send_ui(
            client,
            message.chat.id,
            _center_launcher_text(),
            reply_markup=_center_panel_markup(),
        )

    @client.on_message(dynamic_command("plugin") & filters.me)
    async def cmd_plugin(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        args = _args(message)
        if not args or args[0].casefold() in {"list", "all"}:
            await _send_command_panel(client, message, "DAFTAR PLUGIN", _plugin_lines(list_plugin_status()))
            return
        action = args[0].casefold()
        if action == "info" and len(args) >= 2:
            row = _plugin_row(args[1])
            lines = _plugin_info_lines(row) if row else ["├ Plugin tidak ditemukan atau nama ambigu."]
            await _send_command_panel(client, message, "PLUGIN INFO", lines)
            return
        if action in {"enable", "disable", "reload"} and len(args) >= 2:
            row = _plugin_row(args[1])
            if not row:
                result = "Plugin tidak ditemukan atau nama ambigu."
            elif row["module"] == __name__ and action == "disable":
                result = "Control Panel tidak dapat dinonaktifkan dari dirinya sendiri."
            elif action == "enable":
                if enable_plugin(row["module"]):
                    ok, detail = reload_plugin(client, row["module"])
                    result = "Plugin berhasil diaktifkan." if ok else f"Plugin diaktifkan, tetapi gagal memuat handler: {detail}"
                else:
                    result = "Plugin gagal diaktifkan."
                audit("Enable Plugin", f"{row['module']} user={_owner_id(message)}")
            elif action == "disable":
                result = "Plugin berhasil dinonaktifkan." if disable_plugin(client, row["module"]) else "Plugin gagal dinonaktifkan."
                audit("Disable Plugin", f"{row['module']} user={_owner_id(message)}")
            else:
                ok, detail = reload_plugin(client, row["module"])
                result = detail
                audit("Reload Plugin", f"{row['module']} user={_owner_id(message)}")
            await _send_command_panel(client, message, "PLUGIN MANAGER", [f"├ {result}"])
            return
        if action == "reloadall":
            results = []
            for row in list_plugin_status():
                if row["enabled"] and row["module"] != __name__:
                    ok, detail = reload_plugin(client, row["module"])
                    results.append(f"{'✅' if ok else '❌'} {row['module']}: {detail}")
            audit("Reload Plugin", f"all user={_owner_id(message)}")
            await _send_command_panel(client, message, "RELOAD ALL", results or ["├ Tidak ada plugin aktif untuk dimuat ulang."])
            return
        await _send_command_panel(client, message, "PLUGIN MANAGER", ["├ Format:", "│  ╰➤ `.plugin list`", "│  ╰➤ `.plugin info <plugin>`", "│  ╰➤ `.plugin enable|disable|reload <plugin>`", "│  ╰➤ `.plugin reloadall`"])

    @client.on_message(dynamic_command("theme") & filters.me)
    async def cmd_theme(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        args = _args(message)
        if not args:
            await _send_command_panel(client, message, "THEME ENGINE", [f"├ Tema Aktif\n│  ╰➤ {current()}"], _theme_markup())
            return
        action = args[0].casefold()
        if action == "list":
            lines = [f"├ Tema Aktif\n│  ╰➤ {current()}", "│"]
            lines.extend(f"{'✅' if item['name'] == current() else '▫️'} {item['name']}" for item in available())
            await _send_command_panel(client, message, "DAFTAR TEMA", lines)
        elif action == "set" and len(args) >= 2:
            name = " ".join(args[1:])
            ok = set_active(name)
            if ok:
                audit("Ganti Theme", f"theme={name} user={_owner_id(message)}")
            await _send_command_panel(client, message, "THEME ENGINE", [f"├ {'Tema berhasil diaktifkan.' if ok else 'Tema tidak ditemukan.'}"])
        elif action == "preview" and len(args) >= 2:
            name = " ".join(args[1:])
            item = next((theme for theme in available() if theme["name"].casefold() == name.casefold()), None)
            if item:
                preview = render_theme(item["name"], "THEME PREVIEW", "├ Contoh tampilan Control Panel\n│  ╰➤ Preview berhasil.")
                await send_ui(client, message.chat.id, preview)
            else:
                await _send_command_panel(client, message, "THEME PREVIEW", ["├ Tema tidak ditemukan."])
        else:
            await _send_command_panel(client, message, "THEME ENGINE", ["├ Format: `.theme list`", "├ `.theme set <nama_tema>`", "├ `.theme preview <nama_tema>`"])

    @client.on_message((dynamic_command("dashboard") | dynamic_command("stats")) & filters.me)
    async def cmd_dashboard(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        await _send_command_panel(client, message, "DASHBOARD", _dashboard_lines(), keyboard(nav_rows()))

    @client.on_message(dynamic_command("settings") & filters.me)
    async def cmd_settings(client, message):
        asyncio.create_task(auto_delete(message, delay=AUTO_DELETE_CMD))
        owner = _owner_id(message)
        ensure_user_settings(owner)
        args = _args(message)
        if args:
            ok, detail = _settings_command(owner, args)
            await _send_command_panel(client, message, "SETTINGS", [f"├ {detail}"])
            return
        await _send_command_panel(client, message, "SETTINGS", _settings_lines(owner), _settings_markup(owner))

    @client.on_callback_query(filters.regex(r"^cc:"))
    async def center_callback(client, query):
        await _center_callback_handler(query)

    @client.on_callback_query(filters.regex(r"^cp:"))
    async def cp_callback(client, query):
        await _callback_handler(client, query)
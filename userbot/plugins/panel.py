"""IBEKS Control Panel plugin (UI + navigation only)

Placed at: userbot/plugins/panel.py

Features:
- Provides `.panel` command (OWNER only) to open Control Panel UI.
- All navigation uses edit_message_text/edit_message_reply_markup.
- Defines main menu and submenus. Submenu actions are placeholders (not executing runtime changes).
- Callback data namespace: `ibeks_panel:` prefix.

This plugin implements `setup(client)` so it will be loaded by the existing loader.
"""

from __future__ import annotations

import typing

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup

from config import OWNER_ID, CMD_PREFIX
from plugins.utils.ui import send_ui
from utils.control_ui import keyboard, body, edit_panel, nav_rows
from utils.control_log import record
from loader import plugin_modules

PFX = "ibeks_panel"

# Main menu mapping: key -> (label)
MAIN_MENU = [
    ("plugin", "📦 Plugin Manager"),
    ("store", "🧩 Plugin Store"),
    ("theme", "🎨 Theme Engine"),
    ("dashboard", "📊 Dashboard"),
    ("macro", "⚡ Macro"),
    ("backup", "☁️ Backup"),
    ("update", "🔄 Update"),
    ("permission", "👤 Permission"),
    ("settings", "⚙️ Settings"),
]


def _cb(*parts: str) -> str:
    """Build callback_data with our prefix."""
    return f"{PFX}:{':'.join(parts)}"


def _main_markup() -> InlineKeyboardMarkup:
    # Build a grid of 3 columns
    rows = []
    row = []
    for idx, (key, label) in enumerate(MAIN_MENU, start=1):
        row.append((label, _cb("main", key)))
        if idx % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(nav_rows(back=_cb("main", "home")))
    return keyboard(rows)


async def _show_main(client, message):
    title = "IBEKS Control Panel"
    lines = ["Pilih menu:", ""]
    lines.extend(f"{label}" for _, label in MAIN_MENU)
    markup = _main_markup()
    # send initial UI by editing if message provided, else send new
    if message is None:
        # send new message
        await send_ui(client, client._bot_user.id if hasattr(client, "_bot_user") else message.chat.id, "\n".join(lines), title=title, reply_markup=markup)
    else:
        await edit_panel(message._client, message, title, lines, markup=markup)


# Submenu builders -----------------------------------------------------------

def _submenu_markup(category_key: str, items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [[(label, _cb(category_key, action))] for action, label in items]
    rows.append(nav_rows(back=_cb("main", "home")))
    return keyboard(rows)


async def _show_plugin_manager(query, message):
    title = "Plugin Manager"
    lines = ["Plugin Manager", "Pilih aksi:"]
    items = [
        ("list", "📋 List Plugin"),
        ("enable", "✅ Enable Plugin"),
        ("disable", "❌ Disable Plugin"),
        ("reload", "🔄 Reload Plugin"),
        ("reload_all", "🔃 Reload All"),
        ("info", "ℹ️ Plugin Info"),
    ]
    markup = _submenu_markup("plugin", items)
    await edit_panel(query, title, lines, markup=markup)


async def _show_theme_engine(query, message):
    title = "Theme Engine"
    lines = ["Theme Engine", "Pilih aksi:"]
    items = [
        ("list", "🎨 List Theme"),
        ("set", "🔘 Set Theme"),
        ("preview", "👁 Preview"),
    ]
    markup = _submenu_markup("theme", items)
    await edit_panel(query, title, lines, markup=markup)


async def _show_plugin_store(query, message):
    title = "Plugin Store"
    lines = ["Plugin Store", "Fitur belum tersedia."]
    markup = _submenu_markup("store", [])
    await edit_panel(query, title, lines, markup=markup)


async def _show_dashboard(query, message):
    title = "Dashboard"
    lines = ["Dashboard", "Ringkasan sistem dan plugin."]
    items = [
        ("sys", "📈 System Stats"),
        ("plugins", "🧩 Plugin Stats"),
        ("refresh", "🔄 Refresh"),
    ]
    markup = _submenu_markup("dashboard", items)
    await edit_panel(query, title, lines, markup=markup)


async def _show_macro(query, message):
    title = "Macro"
    lines = ["Macro Manager", "Kelola macro Anda."]
    items = [
        ("list", "📋 List Macro"),
        ("add", "➕ Add Macro"),
        ("edit", "✏️ Edit Macro"),
        ("delete", "🗑 Delete Macro"),
    ]
    markup = _submenu_markup("macro", items)
    await edit_panel(query, title, lines, markup=markup)


async def _show_backup(query, message):
    title = "Backup"
    lines = ["Backup & Restore", "Kelola backup data."]
    items = [
        ("create", "💾 Create Backup"),
        ("list", "📋 List Backup"),
        ("restore", "♻️ Restore"),
    ]
    markup = _submenu_markup("backup", items)
    await edit_panel(query, title, lines, markup=markup)


async def _show_update(query, message):
    title = "Update"
    lines = ["Update", "Periksa & terapkan pembaruan."]
    items = [("check", "🔄 Check Update")]
    markup = _submenu_markup("update", items)
    await edit_panel(query, title, lines, markup=markup)


async def _show_permission(query, message):
    title = "Permission"
    lines = ["Permission Groups", "Kelola role pengguna."]
    items = [
        ("owner", "👑 Owner"),
        ("sudo", "🛡 Sudo"),
        ("pro", "💎 Pro"),
        ("seller", "🛍 Seller"),
        ("fun", "🎮 Fun User"),
    ]
    markup = _submenu_markup("permission", items)
    await edit_panel(query, title, lines, markup=markup)


async def _show_settings(query, message):
    title = "Settings"
    lines = ["General Settings", "Sesuaikan preferensi userbot."]
    items = [
        ("prefix", "Prefix"),
        ("autodelete", "Auto Delete"),
        ("animation", "Animation"),
        ("logger", "Logger"),
        ("emoji_mode", "Emoji Mode"),
        ("theme", "Theme"),
    ]
    markup = _submenu_markup("settings", items)
    await edit_panel(query, title, lines, markup=markup)


# Action placeholders (non-destructive) -------------------------------------

async def _placeholder_action(query, category: str, action: str):
    title = f"{category.title()} - {action.title()}"
    lines = [f"Fitur '{action}' pada kategori '{category}' belum diimplementasikan."]
    markup = keyboard([[("⬅ Back", _cb("main", "home")), ("🏠 Home", _cb("main", "home")), ("❌ Close", _cb("close", "now"))]])
    await edit_panel(query, title, lines, markup=markup)


# Command and callback handlers ---------------------------------------------


def _is_owner(user_id: int) -> bool:
    try:
        return int(OWNER_ID) and int(user_id) == int(OWNER_ID)
    except Exception:
        return False


async def _panel_command(client, message):
    # Owner-only
    if not _is_owner(message.from_user.id if message.from_user else 0):
        await message.reply_text("Panel hanya untuk Owner.")
        return

    title = "IBEKS Control Panel"
    lines = ["Selamat datang di IBEKS Control Panel", "Pilih menu untuk melanjutkan:"]
    markup = _main_markup()
    # send initial message and keep it for edits
    await send_ui(client, message.chat.id, "\n".join(lines), title=title, reply_markup=markup)
    record("panel_open", f"owner={message.from_user.id}")


async def _panel_callback(client, query):
    await query.answer()
    data = (query.data or "").split(":")
    # data format: ibeks_panel:section:action[:...]
    if len(data) < 2:
        return
    _, section, *rest = data
    action = rest[0] if rest else ""

    # Navigation handling
    if section == "main":
        if action == "home" or action == "":
            # show main menu
            await edit_panel(query, "IBEKS Control Panel", ["Pilih menu:"], markup=_main_markup())
            return
        # Map keys to submenu shows
        if action == "plugin":
            await _show_plugin_manager(query, query.message)
            return
        if action == "store":
            await _show_plugin_store(query, query.message)
            return
        if action == "theme":
            await _show_theme_engine(query, query.message)
            return
        if action == "dashboard":
            await _show_dashboard(query, query.message)
            return
        if action == "macro":
            await _show_macro(query, query.message)
            return
        if action == "backup":
            await _show_backup(query, query.message)
            return
        if action == "update":
            await _show_update(query, query.message)
            return
        if action == "permission":
            await _show_permission(query, query.message)
            return
        if action == "settings":
            await _show_settings(query, query.message)
            return

    if section in {"plugin", "theme", "store", "dashboard", "macro", "backup", "update", "permission", "settings"}:
        # action-level placeholder
        if action == "" or action == "home":
            # go back to main menu
            await edit_panel(query, "IBEKS Control Panel", ["Pilih menu:"], markup=_main_markup())
            return
        if action == "close" or section == "close":
            try:
                await client.delete_messages(query.message.chat.id, query.message.id)
            except Exception:
                pass
            return
        # Placeholder for deeper actions
        await _placeholder_action(query, section, action)
        return

    if section == "close":
        # delete message
        try:
            await client.delete_messages(query.message.chat.id, query.message.id)
        except Exception:
            pass
        return


# Plugin contract -----------------------------------------------------------

def setup(client):
    # Register command handler and callback query handler
    client.add_handler(lambda *a, **k: None)  # no-op to satisfy some checker if needed
    client.add_handler  # silence unused
    # Decorators: attach handlers via decorators to integrate with loader's registry
    @client.on_message(filters.command(["panel"], prefixes=CMD_PREFIX) & filters.user(OWNER_ID))
    async def _cmd(client_, message_):
        await _panel_command(client_, message_)

    @client.on_callback_query(filters.regex(rf"^{PFX}:"))
    async def _cb_handler(client_, query_):
        await _panel_callback(client_, query_)


# For manual import in userbot/main.py: expose register

def register(client):
    """Compatibility: userbot.main may import `panel` and call register(client)."""
    setup(client)

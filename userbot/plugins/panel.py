"""IBEKS Control Panel plugin (UI + navigation + READ-ONLY plugin list/info)

Location: userbot/plugins/panel.py

This extends the previously-added panel with read-only features:
- List Plugin (reads from DB)
- Plugin Info (reads metadata + attempts to parse commands from source)

Constraints honored:
- No destructive actions (no enable/disable/reload/etc.)
- No modification of loader or other core files
- Owner-only access
- All navigation uses existing UI helpers and edit_message
- Callback namespace: ibeks_panel:... 
"""

from __future__ import annotations

import ast
import os
from typing import List

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup

from config import OWNER_ID, CMD_PREFIX
from plugins.utils.ui import send_ui
from utils.control_ui import keyboard, edit_panel, nav_rows
from utils.control_log import record
from db import list_plugin_status, get_plugin_status

PFX = "ibeks_panel"

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
    return f"{PFX}:{':'.join(parts)}"


def _encode_module(module: str) -> str:
    # safe reversible encoding for callback_data (avoid ':' collisions)
    return module.replace(".", "|")


def _decode_module(token: str) -> str:
    return token.replace("|", ".")


def _main_markup() -> InlineKeyboardMarkup:
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


async def _show_main(query, message=None):
    title = "IBEKS Control Panel"
    lines = ["Selamat datang di IBEKS Control Panel", "Pilih menu untuk melanjutkan:"]
    markup = _main_markup()
    if query is None:
        # send new message (command path)
        await send_ui(message._client, message.chat.id, "\n".join(lines), title=title, reply_markup=markup)
    else:
        await edit_panel(query, title, lines, markup=markup)


# ---------------- Plugin Manager: List & Info (READ-ONLY) ------------------

def _format_status(row: dict) -> str:
    enabled = "✅ Enabled" if row.get("enabled") else "❌ Disabled"
    loaded = "(Loaded)" if row.get("loaded") else "(Not loaded)"
    return f"{enabled} {loaded}"


async def _show_plugin_manager(query, message):
    title = "Plugin Manager"
    lines = ["Plugin Manager", "Pilih aksi:"]
    items = [
        ("list", "📋 List Plugin"),
        ("info", "🔍 Plugin Info"),
    ]
    rows = [[(label, _cb("plugin", action))] for action, label in items]
    rows.append(nav_rows(back=_cb("main", "home")))
    markup = keyboard(rows)
    await edit_panel(query, title, lines, markup=markup)


async def _show_plugin_list(query, message):
    title = "Plugin List"
    plugins = list_plugin_status()
    if not plugins:
        lines = ["Tidak ada plugin yang terdaftar."]
        markup = keyboard([[("⬅ Back", _cb("main", "plugin")), ("🏠 Home", _cb("main", "home")), ("❌ Close", _cb("close", "now"))]])
        await edit_panel(query, title, lines, markup=markup)
        return

    lines = [f"Total plugin: {len(plugins)}", ""]
    buttons = []
    for p in plugins:
        name = p.get("filename") or p.get("module")
        module = p.get("module")
        status = _format_status(p)
        lines.append(f"• {name} — {status}")
        token = _encode_module(module)
        buttons.append([(name, _cb("plugin", "info_select", token))])

    # paginate plugin buttons into rows of 2
    btn_rows = []
    cur = []
    for row in buttons:
        cur.extend(row)
        if len(cur) >= 2:
            btn_rows.append(cur)
            cur = []
    if cur:
        btn_rows.append(cur)

    nav = [("⬅ Back", _cb("main", "plugin")), ("🏠 Home", _cb("main", "home")), ("❌ Close", _cb("close", "now"))]
    btn_rows.append(nav)
    markup = keyboard(btn_rows)
    await edit_panel(query, title, lines, markup=markup)


async def _show_plugin_info(query, message, module_token: str):
    module = _decode_module(module_token)
    title = "Plugin Info"
    meta = get_plugin_status(module)
    if not meta:
        lines = [f"Plugin '{module}' tidak ditemukan di database."]
        markup = keyboard([[("⬅ Back", _cb("main", "plugin")), ("🏠 Home", _cb("main", "home")), ("❌ Close", _cb("close", "now"))]])
        await edit_panel(query, title, lines, markup=markup)
        return

    lines = []
    lines.append(f"Name: {meta.get('filename')}")
    lines.append(f"Module: {meta.get('module')}")
    lines.append(f"Category: {meta.get('category')}")
    lines.append(f"Version: {meta.get('version')}")
    lines.append(f"Author: {meta.get('author')}")
    lines.append(f"Commands (count): {meta.get('command_count')}")

    cmd_list: List[str] = []
    file_path = meta.get('file_path')
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                src = f.read()
            cmd_list = _extract_commands_from_source(src)
        except Exception:
            cmd_list = []

    if cmd_list:
        lines.append("")
        lines.append("Commands:")
        for c in cmd_list:
            lines.append(f"• {c}")
    else:
        lines.append("")
        lines.append("Commands: (detail tidak tersedia)")

    lines.append("")
    lines.append(f"Status: {('Enabled' if meta.get('enabled') else 'Disabled')} / {('Loaded' if meta.get('loaded') else 'Not loaded')}")
    lines.append(f"File size: {meta.get('file_size')} bytes")
    lines.append(f"Path: {meta.get('file_path')}")

    markup = keyboard([[("⬅ Back", _cb("main", "plugin")), ("🏠 Home", _cb("main", "home")), ("❌ Close", _cb("close", "now"))]])
    await edit_panel(query, title, lines, markup=markup)


# ----------------- Source parsing helper (best-effort, read-only) ---------

def _extract_commands_from_source(source: str) -> List[str]:
    commands: List[str] = []
    try:
        tree = ast.parse(source)
    except Exception:
        return commands

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'dynamic_command':
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    commands.append(arg.value)
        if isinstance(node, ast.Call):
            func = node.func
            func_name = None
            if isinstance(func, ast.Attribute):
                func_name = func.attr
            elif isinstance(func, ast.Name):
                func_name = func.id
            if func_name == 'command':
                if node.args:
                    a0 = node.args[0]
                    if isinstance(a0, ast.List):
                        for elt in a0.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                commands.append(elt.value)
                    elif isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                        commands.append(a0.value)
    seen = set()
    out: List[str] = []
    for c in commands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


# ---------------- Handlers & plugin contract -------------------------------


def _is_owner(user_id: int) -> bool:
    try:
        return int(OWNER_ID) and int(user_id) == int(OWNER_ID)
    except Exception:
        return False


async def _panel_command(client, message):
    if not _is_owner(message.from_user.id if message.from_user else 0):
        await message.reply_text("Panel hanya untuk Owner.")
        return
    title = "IBEKS Control Panel"
    lines = ["Selamat datang di IBEKS Control Panel", "Pilih menu untuk melanjutkan:"]
    markup = _main_markup()
    await send_ui(client, message.chat.id, "\n".join(lines), title=title, reply_markup=markup)
    record("panel_open", f"owner={message.from_user.id}")


async def _panel_callback(client, query):
    await query.answer()
    data = (query.data or "").split(":")
    if len(data) < 2:
        return
    _, section, *rest = data
    action = rest[0] if rest else ""

    # main menu navigation
    if section == 'main':
        if action in ('', 'home'):
            await edit_panel(query, "IBEKS Control Panel", ["Selamat datang di IBEKS Control Panel", "Pilih menu untuk melanjutkan:"], markup=_main_markup())
            return
        if action == 'plugin':
            await _show_plugin_manager(query, query.message)
            return
        # other main menu entries are placeholders
        await edit_panel(query, 'IBEKS Control Panel', [f"Menu '{action}' belum diimplementasikan."], markup=_main_markup())
        return

    # plugin manager sub-actions
    if section == 'plugin':
        if action == 'list':
            await _show_plugin_list(query, query.message)
            return
        if action == 'info':
            await _show_plugin_manager(query, query.message)
            return
        if action == 'info_select' and rest:
            token = rest[0]
            await _show_plugin_info(query, query.message, token)
            return

    if section == 'close':
        try:
            await client.delete_messages(query.message.chat.id, query.message.id)
        except Exception:
            pass
        return

    # generic navigation: back/home
    if action in ('back', 'home'):
        await edit_panel(query, "IBEKS Control Panel", ["Selamat datang di IBEKS Control Panel", "Pilih menu untuk melanjutkan:"], markup=_main_markup())
        return


def setup(client):
    @client.on_message(filters.command(["panel"], prefixes=CMD_PREFIX) & filters.user(OWNER_ID))
    async def _cmd(client_, message_):
        await _panel_command(client_, message_)

    @client.on_callback_query(filters.regex(rf"^{PFX}:"))
    async def _cb_handler(client_, query_):
        await _panel_callback(client_, query_)


def register(client):
    setup(client)

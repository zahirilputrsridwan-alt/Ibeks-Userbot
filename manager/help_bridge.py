"""Bridge Help: Userbot meminta UI, Manager Bot mengirim dan mengeditnya."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup

from config import DATABASE_PATH, USERBOT_SOURCE_DIR, USERBOT_RUNTIME_DIR
from logger import log


_HELP_BUILDER_PATH = USERBOT_SOURCE_DIR / "utils" / "help_builder.py"
_HELP_BUILDER_SPEC = importlib.util.spec_from_file_location(
    "ibeks_help_builder",
    _HELP_BUILDER_PATH,
)
if _HELP_BUILDER_SPEC is None or _HELP_BUILDER_SPEC.loader is None:
    raise ImportError(f"Help builder tidak ditemukan: {_HELP_BUILDER_PATH}")
_HELP_BUILDER = importlib.util.module_from_spec(_HELP_BUILDER_SPEC)
sys.modules[_HELP_BUILDER_SPEC.name] = _HELP_BUILDER
_HELP_BUILDER_SPEC.loader.exec_module(_HELP_BUILDER)

build_category_text = _HELP_BUILDER.build_category_text
build_home_text = _HELP_BUILDER.build_home_text
category_keyboard = _HELP_BUILDER.category_keyboard
clamp_page = _HELP_BUILDER.clamp_page
get_plan = _HELP_BUILDER.get_plan
home_keyboard = _HELP_BUILDER.home_keyboard
page_count = _HELP_BUILDER.page_count
scan_plugins = _HELP_BUILDER.scan_plugins
total_plugins = _HELP_BUILDER.total_plugins


CALLBACK_FILTER = filters.regex(
    r"^(?:help_home|help_page(?::\d+)?|help_category:[^:]+:\d+|help_back(?::\d+)?)$"
)
REQUEST_POLL_INTERVAL = 0.25


@dataclass(frozen=True)
class HelpContext:
    """Konteks yang diperlukan untuk merender ulang pesan Help bot."""

    user_id: int
    owner: str
    prefix: str


_contexts: dict[tuple[int, int], HelpContext] = {}
_watcher_task: asyncio.Task | None = None


def _plugin_root() -> Path:
    return USERBOT_SOURCE_DIR / "plugins"


def _request_paths() -> list[Path]:
    if not USERBOT_RUNTIME_DIR.exists():
        return []
    return sorted(USERBOT_RUNTIME_DIR.glob("*/.help_request.json"))


def _read_request(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            "chat_id": int(payload["chat_id"]),
            "user_id": int(payload["user_id"]),
            "owner": str(payload.get("owner") or payload["user_id"]),
            "prefix": str(payload.get("prefix") or "."),
        }
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log.warning("[Help] Request invalid dari %s: %s", path, exc)
        try:
            path.unlink()
        except OSError:
            pass
        return None


async def _owner_name(client, fallback: str) -> str:
    try:
        user = await client.get_me()
        return user.first_name or user.username or fallback
    except Exception:
        return fallback


def _home_payload(context: HelpContext, page: int):
    catalog = scan_plugins(_plugin_root())
    page = clamp_page(catalog, page)
    text = build_home_text(
        plan=get_plan(context.user_id, DATABASE_PATH),
        prefix=context.prefix,
        plugins=total_plugins(catalog),
        owner=context.owner,
        page=page,
        pages=page_count(catalog),
    )
    markup = home_keyboard(catalog, page)
    return catalog, text, markup, page


async def _edit_message(client, message, text: str, markup: InlineKeyboardMarkup):
    """Edit bubble yang sama dan selalu memasang keyboard inline."""
    try:
        return await client.edit_message_text(
            message.chat.id,
            message.id,
            text,
            reply_markup=markup,
        )
    except RPCError:
        return await client.edit_message_reply_markup(
            message.chat.id,
            message.id,
            reply_markup=markup,
        )


async def _send_help(client, payload: dict) -> None:
    context = HelpContext(
        user_id=payload["user_id"],
        owner=await _owner_name(client, payload["owner"]),
        prefix=payload["prefix"],
    )
    _catalog, text, markup, _page = _home_payload(context, 0)
    if not isinstance(markup, InlineKeyboardMarkup):
        raise TypeError("Help home harus menghasilkan InlineKeyboardMarkup")
    message = await client.send_message(
        payload["chat_id"],
        text,
        reply_markup=markup,
    )
    _contexts[(message.chat.id, message.id)] = context
    log.info(
        "[Help] UI terkirim via BOT_TOKEN chat_id=%s message_id=%s categories=%s.",
        message.chat.id,
        message.id,
        len(_catalog),
    )
    # Batasi memory konteks agar request Help berulang tidak menumbuhkan dict.
    if len(_contexts) > 1000:
        for key in list(_contexts)[:200]:
            _contexts.pop(key, None)


async def _watch_requests(client) -> None:
    while True:
        try:
            for path in _request_paths():
                log.info("[Help] Request terdeteksi: %s.", path)
                payload = _read_request(path)
                if payload is None:
                    continue
                try:
                    await _send_help(client, payload)
                    path.unlink(missing_ok=True)
                except Exception as exc:
                    log.exception(
                        "[Help] Gagal mengirim UI Help dari %s: %s.",
                        path,
                        exc,
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("[Help] Watcher request gagal.")
        await asyncio.sleep(REQUEST_POLL_INTERVAL)


async def _handle_callback(client, query) -> None:
    try:
        await query.answer()
        message = query.message
        if not message:
            return

        context = _contexts.get((message.chat.id, message.id))
        if context is None:
            await query.answer(
                "Help sudah kedaluwarsa. Jalankan .help lagi.",
                show_alert=True,
            )
            return

        data = query.data or ""
        if isinstance(data, bytes):
            data = data.decode(errors="ignore")
        catalog = scan_plugins(_plugin_root())

        if data == "help_home":
            _catalog, text, markup, _page = _home_payload(context, 0)
            await _edit_message(client, message, text, markup)
            log.info("[Help] Callback help_home message_id=%s.", message.id)
            return

        if data.startswith("help_page:"):
            try:
                page = int(data.split(":", 1)[1])
            except ValueError:
                page = 0
            _catalog, text, markup, _page = _home_payload(context, page)
            await _edit_message(client, message, text, markup)
            log.info(
                "[Help] Callback help_page page=%s message_id=%s.",
                page,
                message.id,
            )
            return

        if data.startswith("help_category:"):
            _, key, raw_page = data.split(":", 2)
            try:
                previous_page = int(raw_page)
            except ValueError:
                previous_page = 0
            category = catalog.get(key)
            if category is None:
                _catalog, text, markup, _page = _home_payload(
                    context,
                    previous_page,
                )
                await _edit_message(client, message, text, markup)
                return
            text = build_category_text(
                category=category,
                plan=get_plan(context.user_id, DATABASE_PATH),
                prefix=context.prefix,
                plugins=total_plugins(catalog),
                owner=context.owner,
            )
            await _edit_message(
                client,
                message,
                text,
                category_keyboard(previous_page),
            )
            log.info(
                "[Help] Callback help_category category=%s message_id=%s.",
                key,
                message.id,
            )
            return

        if data.startswith("help_back:"):
            try:
                page = int(data.split(":", 1)[1])
            except ValueError:
                page = 0
            _catalog, text, markup, _page = _home_payload(context, page)
            await _edit_message(client, message, text, markup)
            log.info(
                "[Help] Callback help_back page=%s message_id=%s.",
                page,
                message.id,
            )
    except Exception:
        log.exception("[Help] Callback gagal diproses.")
        try:
            await query.answer("Help gagal diperbarui.", show_alert=True)
        except Exception:
            log.exception("[Help] Gagal mengirim alert callback.")


def start_help_bridge(client) -> None:
    """Daftarkan callback bot dan mulai watcher IPC Userbot."""
    global _watcher_task
    client.add_handler(CallbackQueryHandler(_handle_callback, CALLBACK_FILTER))
    if _watcher_task is None or _watcher_task.done():
        _watcher_task = client.loop.create_task(_watch_requests(client))
    log.info("[Help] Bridge BOT_TOKEN aktif; watcher request Userbot siap.")
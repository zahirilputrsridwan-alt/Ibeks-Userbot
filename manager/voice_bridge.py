"""Bridge Voice Chat: Userbot publica resultado, Manager hospeda o painel."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import USERBOT_RUNTIME_DIR
from logger import log


REQUEST_POLL_INTERVAL = 0.25
CALLBACK_FILTER = filters.regex(
    r"^voice:(onmic|offmic|leave|refresh):\d+$"
)


@dataclass
class VoicePanel:
    user_id: int
    group_chat_id: int
    message_id: int
    room: str
    connected: bool
    mic_muted: bool | None = None
    last_action: str = "join"
    reason: str = ""


_panels: dict[tuple[int, int], VoicePanel] = {}
_latest_panels: dict[int, tuple[int, int]] = {}
_watcher_task: asyncio.Task | None = None


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temporary_file:
            json.dump(payload, temporary_file, ensure_ascii=False)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass


def _read_payload(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        log.warning("[Voice] IPC inválido em %s: %s", path, exc)
        return None


def _request_paths() -> list[Path]:
    if not USERBOT_RUNTIME_DIR.exists():
        return []
    return sorted(USERBOT_RUNTIME_DIR.glob("*/.voice_request.json"))


def _response_paths() -> list[Path]:
    if not USERBOT_RUNTIME_DIR.exists():
        return []
    return sorted(USERBOT_RUNTIME_DIR.glob("*/.voice_response.json"))


def _keyboard(panel: VoicePanel) -> InlineKeyboardMarkup | None:
    if not panel.connected:
        return None
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎤 On Mic", callback_data=f"voice:onmic:{panel.user_id}"),
                InlineKeyboardButton("🔇 Off Mic", callback_data=f"voice:offmic:{panel.user_id}"),
            ],
            [
                InlineKeyboardButton("🚪 Leave VC", callback_data=f"voice:leave:{panel.user_id}"),
                InlineKeyboardButton("🔄 Refresh", callback_data=f"voice:refresh:{panel.user_id}"),
            ],
        ]
    )


def _panel_text(panel: VoicePanel) -> str:
    if panel.last_action == "leave":
        if not panel.connected:
            return (
                "⚠️ Join Voice Chat Result\n\n"
                "🚪 Left Voice Chat\n\n"
                f"Room :\n{panel.room}\n\n"
                "⨱ IBEKS USERBOT ⨱"
            )

    if not panel.connected:
        reason = panel.reason or "Userbot gagal terhubung ke Voice Chat."
        return (
            "⚠️ Join Voice Chat Result\n\n"
            "❌ Failed\n\n"
            f"Reason :\n{reason}\n\n"
            "⨱ IBEKS USERBOT ⨱"
        )

    mic_status = ""
    if panel.mic_muted is False:
        mic_status = "\n\n🎤 Mic : On"
    elif panel.mic_muted is True:
        mic_status = "\n\n🔇 Mic : Off"
    action_error = f"\n\n❌ {panel.reason}" if panel.reason else ""
    return (
        "⚠️ Join Voice Chat Result\n\n"
        "✅ Success\n\n"
        f"Room :\n{panel.room}"
        f"{mic_status}"
        f"{action_error}\n\n"
        "⨱ IBEKS USERBOT ⨱"
    )


async def _edit_panel(client, panel: VoicePanel) -> None:
    await client.edit_message_text(
        panel.user_id,
        panel.message_id,
        _panel_text(panel),
        reply_markup=_keyboard(panel),
    )


def _panel_for(user_id: int, message_id: int) -> VoicePanel | None:
    panel = _panels.get((user_id, message_id))
    if panel is not None:
        return panel
    key = _latest_panels.get(user_id)
    return _panels.get(key) if key else None


async def _send_panel(client, payload: dict) -> None:
    user_id = int(payload["user_id"])
    panel = VoicePanel(
        user_id=user_id,
        group_chat_id=int(payload["group_chat_id"]),
        message_id=0,
        room=str(payload.get("room") or "Unknown"),
        connected=bool(payload.get("success")),
        last_action="join",
        reason=str(payload.get("reason") or ""),
    )
    message = await client.send_message(
        user_id,
        _panel_text(panel),
        reply_markup=_keyboard(panel),
    )
    panel.message_id = message.id
    key = (user_id, message.id)
    _panels[key] = panel
    _latest_panels[user_id] = key
    log.info(
        "[Voice] Panel terkirim ke user_id=%s message_id=%s group_chat_id=%s.",
        user_id,
        message.id,
        panel.group_chat_id,
    )


async def _apply_response(client, payload: dict) -> None:
    user_id = int(payload["user_id"])
    message_id = int(payload.get("message_id") or 0)
    panel = _panel_for(user_id, message_id)
    if panel is None:
        log.warning("[Voice] Response tanpa panel untuk user_id=%s.", user_id)
        return

    panel.connected = bool(payload.get("connected"))
    panel.last_action = str(payload.get("action") or panel.last_action)
    panel.reason = str(payload.get("reason") or "")
    if "room" in payload and payload["room"]:
        panel.room = str(payload["room"])
    if payload.get("mic_muted") is not None:
        panel.mic_muted = bool(payload["mic_muted"])
    await _edit_panel(client, panel)


async def _handle_callback(client, query) -> None:
    message = query.message
    if not message or getattr(message.chat, "type", None) != "private":
        await query.answer("Panel Voice Chat hanya tersedia di chat pribadi.", show_alert=True)
        return

    data = query.data or ""
    if isinstance(data, bytes):
        data = data.decode(errors="ignore")
    try:
        _prefix, action, raw_user_id = data.split(":", 2)
        user_id = int(raw_user_id)
    except (ValueError, AttributeError):
        await query.answer("Aksi Voice Chat tidak valid.", show_alert=True)
        return

    if query.from_user is None or int(query.from_user.id) != user_id:
        await query.answer("Panel ini bukan milik Anda.", show_alert=True)
        return

    panel = _panels.get((user_id, message.id))
    if panel is None:
        await query.answer("Panel Voice Chat sudah kedaluwarsa.", show_alert=True)
        return

    action_path = USERBOT_RUNTIME_DIR / str(user_id) / ".voice_action.json"
    _atomic_write(
        action_path,
        {
            "action": action,
            "user_id": user_id,
            "group_chat_id": panel.group_chat_id,
            "message_id": panel.message_id,
        },
    )
    await query.answer()


async def _watch_requests(client) -> None:
    while True:
        try:
            if client.is_connected:
                for path in _request_paths():
                    payload = _read_payload(path)
                    path.unlink(missing_ok=True)
                    if payload is None:
                        continue
                    try:
                        await _send_panel(client, payload)
                    except Exception:
                        log.exception("[Voice] Gagal enviar panel.")

                for path in _response_paths():
                    payload = _read_payload(path)
                    path.unlink(missing_ok=True)
                    if payload is None:
                        continue
                    try:
                        await _apply_response(client, payload)
                    except RPCError:
                        log.warning("[Voice] Panel %s não pôde ser editado.", path)
                    except Exception:
                        log.exception("[Voice] Gagal atualizar panel.")
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("[Voice] Watcher IPC gagal; polling tetap berjalan.")
        await asyncio.sleep(REQUEST_POLL_INTERVAL)


def start_voice_bridge(client) -> None:
    """Registra callbacks do Manager e inicia o watcher IPC Voice Chat."""
    global _watcher_task
    client.add_handler(CallbackQueryHandler(_handle_callback, CALLBACK_FILTER))
    if _watcher_task is None or _watcher_task.done():
        _watcher_task = client.loop.create_task(_watch_requests(client))
    log.info("[Voice] Bridge BOT_TOKEN aktif; panel dan callback siap.")
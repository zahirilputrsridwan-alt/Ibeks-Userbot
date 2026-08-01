"""IBEKS USERBOT - UI helpers untuk pesan Telegram."""

from __future__ import annotations

from html import escape
from typing import Optional

from utils.logger import log

FOOTER = "⨱ IBEKS USERBOT ⨱"


def safe_text(text: Optional[str]) -> str:
    return "" if text is None else str(text)


def escape_html(text: Optional[str]) -> str:
    return escape(safe_text(text), quote=False)


def build_header(title: str, category: str = "INFO") -> str:
    return f"╭━━━━━━━━━━━━━━━━━━━━╮\n        {category} | {title}\n╰━━━━━━━━━━━━━━━━━━━━╯"


def build_footer() -> str:
    return FOOTER


def build_message(title: str, body: str, category: str = "INFO", status: str = "INFO", expandable: bool = True) -> str:
    body_html = escape_html(body)
    return _build_message_html(title, body_html, category=category, expandable=expandable)


def _build_message_html(title: str, body_html: str, category: str = "INFO", expandable: bool = True) -> str:
    parts = [build_header(title, category)]
    if body_html.strip():
        parts.append(f"<blockquote{' expandable' if expandable else ''}>\n{body_html}\n</blockquote>")
    parts.append(build_footer())
    return "\n\n".join(parts)


def build_progress_bar(percent: int, width: int = 10) -> str:
    percent = max(0, min(100, int(percent)))
    filled = round(percent / 100 * width)
    return f"{'▰' * filled}{'▱' * (width - filled)} {percent}%"


def _build_report_body(fields: list[tuple[str, str]]) -> str:
    return "\n".join(f"{escape_html(label)} : <code>{escape_html(value)}</code>" for label, value in fields)


def build_report(title: str, fields: list[tuple[str, str]], category: str = "REPORT", status: str = "INFO") -> str:
    return _build_message_html(
        title,
        _build_report_body(fields),
        category=category,
        expandable=True,
    )


def build_success(text: str, title: str = "BERHASIL", category: str = "SUCCESS") -> str:
    return build_message(title, f"✅ {text}", category=category, status="SUCCESS", expandable=True)


def build_error(text: str, title: str = "GAGAL", category: str = "ERROR") -> str:
    return build_message(title, f"❌ {text}", category=category, status="ERROR", expandable=True)


def build_warning(text: str, title: str = "PERINGATAN", category: str = "WARNING") -> str:
    return build_message(title, f"⚠️ {text}", category=category, status="WARNING", expandable=True)


def build_loading(text: str, title: str = "MEMPROSES", category: str = "LOADING") -> str:
    return build_message(title, f"🔄 {text}", category=category, status="LOADING", expandable=True)


def _build_plain_text_message(title: str, body: str) -> str:
    text_body = safe_text(body).strip()
    return "\n\n".join(part for part in (build_header(title), text_body, build_footer()) if part)


async def send_ui(client, chat_id: int, body: str, title: str, category: str, status: str, expandable: bool = True):
    html_expandable = build_message(title, body, category=category, status=status, expandable=True)
    html_plain = build_message(title, body, category=category, status=status, expandable=False)
    plain_text = _build_plain_text_message(title, body)
    attempts = [
        (html_expandable if expandable else html_plain, dict(parse_mode="HTML", disable_web_page_preview=True)),
        (html_plain, dict(parse_mode="HTML", disable_web_page_preview=True)),
        (plain_text, dict(disable_web_page_preview=True)),
    ]
    last_exc = None
    for text, kwargs in attempts:
        try:
            return await client.send_message(chat_id, text, **kwargs)
        except Exception as exc:
            last_exc = exc
            log.warning("[UI] send_ui gagal (%s): %s", kwargs.get("parse_mode"), exc)
    if last_exc:
        raise last_exc
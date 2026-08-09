"""Transport teks UI yang sudah diformat oleh masing-masing plugin."""

from __future__ import annotations

import html
import re

from pyrogram.enums import ParseMode


_BOX_FOOTER = "⨱ IBEKS USERBOT ⨱"
_LEGACY_FOOTER = re.compile(
    r"\n?│\n╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱\s*$"
)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_MIN_EXPANDABLE_LINES = 6
_EXPANDABLE_SPACER = "<br>\u2063<br>\u2063"


def _expandable_html(body: str) -> str:
    """Letakkan body di blockquote expandable dengan footer di luar."""
    text = str(body or "").strip()
    text = _LEGACY_FOOTER.sub("", text).strip()
    lines = text.splitlines()
    if len(lines) < _MIN_EXPANDABLE_LINES:
        lines.extend("│" for _ in range(_MIN_EXPANDABLE_LINES - len(lines)))
        text = "\n".join(lines)
    text = html.escape(text, quote=False)
    text = _INLINE_CODE.sub(r"<code>\1</code>", text)
    return (
        f"<blockquote expandable>\n{text}\n{_EXPANDABLE_SPACER}"
        f"\n</blockquote>\n\n<b>{_BOX_FOOTER}</b>"
    )


async def send_ui(
    client,
    chat_id: int,
    body: str,
    title: str = "",
    category: str = "",
    status: str = "",
    expandable: bool = False,
    reply_markup=None,
    **kwargs,
):
    """Kirim teks yang sudah dirakit langsung oleh plugin pemanggil."""
    if expandable:
        kwargs["parse_mode"] = ParseMode.HTML
        body = _expandable_html(body)
    return await client.send_message(
        chat_id,
        str(body or "").strip(),
        reply_markup=reply_markup,
        **kwargs,
    )


async def edit_ui(
    client,
    message,
    body: str,
    title: str = "",
    emoji: str = "📦",
    reply_markup=None,
    expandable: bool = False,
    **kwargs,
):
    """Edit dengan teks yang sudah dirakit langsung oleh plugin pemanggil."""
    if expandable:
        kwargs["parse_mode"] = ParseMode.HTML
        body = _expandable_html(body)
    # gunakan message.chat.id dan message.message_id untuk kompatibilitas Pyrogram
    return await client.edit_message_text(
        message.chat.id,
        message.message_id,
        str(body or "").strip(),
        reply_markup=reply_markup,
        **kwargs,
    )

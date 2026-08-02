"""Expandable blockquote messages for Telegram Userbot reports.

Telegram renders ``MessageEntityBlockquote(collapsed=True)`` as a native
expand/collapse control.  The report remains part of one message, while the
header and footer stay visible when the report is collapsed.
"""

from __future__ import annotations

from io import BytesIO
from typing import Optional

from pyrogram.raw.core import TLObject
from pyrogram.raw.core.primitives import Int


def _utf16_length(value: str) -> int:
    """Return Telegram's UTF-16 code-unit length for a Python string."""
    return len(value.encode("utf-16-le")) // 2


class _RawExpandableBlockquote(TLObject):
    """Layer-227 expandable blockquote entity.

    Pyrogram 2.0.106 knows the older non-collapsible constructor, so the
    current constructor is serialized locally and passed through Pyrogram's
    normal ``entities`` argument.
    """

    __slots__ = ("collapsed", "offset", "length")
    ID = 0xF1CCAAAC
    QUALNAME = "types.MessageEntityBlockquote"

    def __init__(self, *, collapsed: bool, offset: int, length: int) -> None:
        self.collapsed = bool(collapsed)
        self.offset = int(offset)
        self.length = int(length)

    @staticmethod
    def read(b: BytesIO, *args):
        flags = Int.read(b)
        return _RawExpandableBlockquote(
            collapsed=bool(flags & 1),
            offset=Int.read(b),
            length=Int.read(b),
        )

    def write(self, *args) -> bytes:
        buffer = BytesIO()
        buffer.write(Int(self.ID, False))
        buffer.write(Int(1 if self.collapsed else 0))
        buffer.write(Int(self.offset))
        buffer.write(Int(self.length))
        return buffer.getvalue()


class ExpandableBlockquoteEntity:
    """High-level entity adapter accepted by Pyrogram 2.0.106."""

    __slots__ = ("collapsed", "offset", "length", "_client")

    def __init__(self, *, collapsed: bool, offset: int, length: int) -> None:
        self.collapsed = bool(collapsed)
        self.offset = int(offset)
        self.length = int(length)
        self._client = None

    async def write(self) -> _RawExpandableBlockquote:
        return _RawExpandableBlockquote(
            collapsed=self.collapsed,
            offset=self.offset,
            length=self.length,
        )


def build_expandable(
    header: str,
    report: str,
    footer: str,
    *,
    divider: str = "━━━━━━ ★ ━━━━━━",
    collapsed: bool = True,
) -> tuple[str, list[ExpandableBlockquoteEntity]]:
    """Build one report message and its native expandable entity."""
    header = "" if header is None else str(header)
    report = "" if report is None else str(report)
    footer = "" if footer is None else str(footer)
    divider = "" if divider is None else str(divider)

    prefix = f"{header}\n{divider}\n\n"
    suffix = f"\n\n{footer}"
    text = f"{prefix}{report}{suffix}"
    entity = ExpandableBlockquoteEntity(
        collapsed=collapsed,
        offset=_utf16_length(prefix),
        length=_utf16_length(report),
    )
    return text, [entity]


async def send_expandable(
    client,
    chat_id: int,
    header: str,
    report: str,
    footer: str,
    *,
    divider: str = "━━━━━━ ★ ━━━━━━",
    collapsed: bool = True,
    **kwargs,
):
    """Send a native expandable report as exactly one Telegram message."""
    text, entities = build_expandable(
        header,
        report,
        footer,
        divider=divider,
        collapsed=collapsed,
    )
    kwargs = dict(kwargs)
    kwargs.pop("parse_mode", None)
    return await client.send_message(
        chat_id,
        text,
        parse_mode=None,
        entities=entities,
        **kwargs,
    )


async def edit_expandable(
    client,
    message,
    header: str,
    report: str,
    footer: str,
    *,
    divider: str = "━━━━━━ ★ ━━━━━━",
    collapsed: bool = True,
    **kwargs,
):
    """Edit the existing message while preserving its expandable report."""
    text, entities = build_expandable(
        header,
        report,
        footer,
        divider=divider,
        collapsed=collapsed,
    )
    kwargs = dict(kwargs)
    kwargs.pop("parse_mode", None)
    return await client.edit_message_text(
        message.chat.id,
        message.id,
        text,
        parse_mode=None,
        entities=entities,
        **kwargs,
    )
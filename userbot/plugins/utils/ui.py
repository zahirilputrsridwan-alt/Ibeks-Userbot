"""Transport helper untuk menambahkan expandable blockquote tanpa mengubah UI."""

from __future__ import annotations

from io import BytesIO
from typing import Optional

from pyrogram.parser import Parser
from pyrogram.parser import utils as parser_utils
from pyrogram.raw.core import TLObject
from pyrogram.raw.core.primitives import Int

from utils.logger import log


class _ExpandableBlockquote(TLObject):
    """Telegram layer 227 blockquote entity with collapsed flag."""

    __slots__ = ["collapsed", "offset", "length"]
    ID = 0xF1CCAAAC
    QUALNAME = "types.MessageEntityBlockquote"

    def __init__(self, *, collapsed: bool, offset: int, length: int) -> None:
        self.collapsed = collapsed
        self.offset = offset
        self.length = length

    @staticmethod
    def read(b: BytesIO, *args):
        flags = Int.read(b)
        return _ExpandableBlockquote(
            collapsed=bool(flags & 1),
            offset=Int.read(b),
            length=Int.read(b),
        )

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        b.write(Int(1 if self.collapsed else 0))
        b.write(Int(self.offset))
        b.write(Int(self.length))
        return b.getvalue()


def safe_text(text: Optional[str]) -> str:
    return "" if text is None else str(text)


async def send_ui(
    client,
    chat_id: int,
    body: str,
    title: str = "",
    category: str = "",
    status: str = "",
    expandable: bool = True,
    **kwargs,
):
    """Kirim teks lama dengan blockquote sebagai satu-satunya tambahan UI.

    Argumen title/category/status dipertahankan agar pemanggil lama tetap
    kompatibel, tetapi sengaja tidak dipakai untuk menyusun ulang teks.
    """
    text = safe_text(body)
    send_kwargs = dict(kwargs)

    if expandable and text:
        try:
            parsed = await Parser(None).parse(text)
            parsed_text = parsed["message"]
            entities = list(parsed.get("entities") or [])
            entities.append(
                _ExpandableBlockquote(
                    collapsed=True,
                    offset=0,
                    length=len(parser_utils.add_surrogates(parsed_text)),
                )
            )
            return await client.send_message(
                chat_id,
                parsed_text,
                parse_mode=None,
                entities=entities,
                **send_kwargs,
            )
        except Exception as exc:
            log.warning("[UI] Expandable blockquote gagal, kirim UI lama: %s", exc)

    return await client.send_message(chat_id, text, **send_kwargs)


async def edit_ui(client, message, body: str, reply_markup=None, **kwargs):
    """Edit pesan dengan parser/entity UI yang sama seperti send_ui()."""
    text = safe_text(body)
    try:
        parsed = await Parser(None).parse(text)
        parsed_text = parsed["message"]
        entities = list(parsed.get("entities") or [])
        if parsed_text:
            entities.append(
                _ExpandableBlockquote(
                    collapsed=True,
                    offset=0,
                    length=len(parser_utils.add_surrogates(parsed_text)),
                )
            )
        return await client.edit_message_text(
            message.chat.id,
            message.id,
            parsed_text,
            parse_mode=None,
            entities=entities,
            reply_markup=reply_markup,
            **kwargs,
        )
    except Exception as exc:
        log.warning("[UI] Edit expandable blockquote gagal, edit UI lama: %s", exc)
        return await client.edit_message_text(
            message.chat.id,
            message.id,
            text,
            reply_markup=reply_markup,
            **kwargs,
        )
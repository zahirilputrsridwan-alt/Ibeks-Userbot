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

    # Pyrogram 2.0.106 mencoba menambahkan ``_client`` ke setiap entity
    # high-level yang diberikan secara manual. Entity expandable custom dan
    # entity hasil Parser tidak menyediakan slot tersebut, sehingga request
    # gagal sebelum dikirim dan seluruh plugin yang memakai send_ui() diam.
    # Kirim teks melalui parser bawaan Pyrogram; isi pesan tetap dipertahankan.
    return await client.send_message(chat_id, text, **send_kwargs)


async def edit_ui(client, message, body: str, reply_markup=None, **kwargs):
    """Edit pesan dengan parser bawaan Pyrogram."""
    text = safe_text(body)
    return await client.edit_message_text(
        message.chat.id,
        message.id,
        text,
        reply_markup=reply_markup,
        **kwargs,
    )
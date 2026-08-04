"""Transport teks UI yang sudah diformat oleh masing-masing plugin."""

from __future__ import annotations

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
    """Kirim teks yang sudah dirakit langsung oleh plugin pemanggil."""
    return await client.send_message(chat_id, str(body or "").strip(), **kwargs)


async def edit_ui(
    client,
    message,
    body: str,
    title: str = "",
    emoji: str = "📦",
    reply_markup=None,
    **kwargs,
):
    """Edit dengan teks yang sudah dirakit langsung oleh plugin pemanggil."""
    return await client.edit_message_text(
        message.chat.id,
        message.id,
        str(body or "").strip(),
        reply_markup=reply_markup,
        **kwargs,
    )
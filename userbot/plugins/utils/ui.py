"""Format dan transport UI teks IBEKS USERBOT."""

from __future__ import annotations

from typing import Optional


def safe_text(text: Optional[str]) -> str:
    return "" if text is None else str(text).strip()


def box_text(body: str, title: str = "", emoji: str = "📦") -> str:
    """Ubah isi teks menjadi satu-satunya format kartu teks Userbot."""
    text = safe_text(body)
    if text.startswith("╭─「 ") and text.endswith("⨱"):
        return text
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    inferred_title = title.strip() or (lines[0] if lines else "Informasi")
    if not title and lines:
        lines = lines[1:]
    rows = [f"╭─「 {emoji} 𝗝𝗨𝗗𝗨𝗟 {inferred_title} 」", "│"]
    if not lines:
        lines = ["Tidak ada informasi."]
    for line in lines:
        if ":" in line:
            label, value = line.split(":", 1)
            label, value = label.strip(), value.strip()
        else:
            label, value = "Info", line
        rows.extend((f"├ 🔹 𝗟𝗮𝗯𝗲𝗹 {label}", f"│  ╰➤ {value}", "│"))
    rows.append("╰─ ⨱ 𝗜𝗕𝗘𝗞𝗦 𝗨𝗦𝗘𝗥𝗕𝗢𝗧 ⨱")
    return "\n".join(rows)


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
    """Kirim output teks dalam kartu UI baru."""
    text = box_text(body, title=title or category or status)
    send_kwargs = dict(kwargs)
    return await client.send_message(chat_id, text, **send_kwargs)


async def edit_ui(
    client,
    message,
    body: str,
    title: str = "",
    emoji: str = "📦",
    reply_markup=None,
    **kwargs,
):
    """Edit pesan dengan kartu UI baru."""
    text = box_text(body, title=title, emoji=emoji)
    return await client.edit_message_text(
        message.chat.id,
        message.id,
        text,
        reply_markup=reply_markup,
        **kwargs,
    )
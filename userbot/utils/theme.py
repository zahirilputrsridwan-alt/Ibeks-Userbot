"""Theme Engine untuk seluruh fitur Control Panel baru."""

from __future__ import annotations

from db import active_theme, list_themes, save_theme


THEME_EMOJI = {
    "Premium": "💎",
    "Freeze": "❄️",
    "Minimal": "▣",
    "Neon": "⚡",
    "Matrix": "🟢",
}


def available() -> list[dict]:
    return list_themes()


def current() -> str:
    return active_theme()


def set_active(name: str) -> bool:
    """Aktifkan tema yang sudah terdaftar."""
    match = next((item for item in list_themes() if item["name"].casefold() == name.casefold()), None)
    if not match:
        return False
    save_theme(match["name"], match["definition"], active=True)
    return True


def render(title: str, body: str = "", status: str = "") -> str:
    """Render satu blok UI konsisten sesuai tema aktif."""
    return render_theme(current(), title, body, status=status)


def render_theme(name: str, title: str, body: str = "", status: str = "") -> str:
    """Render tema tertentu untuk preview tanpa mengubah tema aktif."""
    row = next(
        (item for item in list_themes() if item["name"].casefold() == name.casefold()),
        None,
    )
    template = (row or {}).get(
        "definition", "╭─「 {title} 」\n│\n{body}\n│\n╰─ ⨱ IBEKS USERBOT ⨱"
    )
    rendered = template.format(title=title, body=body.strip())
    if status:
        rendered = f"{rendered}\n\n{status}"
    return rendered.strip()


def emoji(name: str) -> str:
    return THEME_EMOJI.get(current(), "◈")
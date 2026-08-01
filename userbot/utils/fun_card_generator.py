"""
Generator kartu Fun untuk .cardp dan .cardw.

Kartu dibuat dalam resolusi 1280x720 dengan gaya HUD futuristik yang
terinspirasi referensi ID card: panel gelap, garis neon, lingkaran foto,
progress bar, barcode, dan QR sederhana.
"""

import hashlib
import io
import os
from datetime import datetime, timezone
from typing import Iterable, Optional, Tuple

import qrcode
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client
from pyrogram.types import User

from utils.fun_data import CCANTIK_AURA, CCANTIK_TIER, CTAMPAN_AURA, CTAMPAN_TIER
from utils.id_data import STATUS_MENTAL
from utils.logger import log


CARD_WIDTH = 1280
CARD_HEIGHT = 720
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

MALE_PALETTE = {
    "background": (5, 10, 9),
    "panel": (11, 22, 17),
    "panel_alt": (16, 31, 20),
    "accent": (181, 255, 0),
    "accent_alt": (55, 255, 122),
    "accent_dim": (54, 115, 59),
    "text": (244, 255, 244),
    "muted": (154, 181, 164),
}

FEMALE_PALETTE = {
    "background": (15, 7, 16),
    "panel": (31, 13, 29),
    "panel_alt": (48, 18, 42),
    "accent": (255, 111, 207),
    "accent_alt": (177, 255, 82),
    "accent_dim": (130, 57, 119),
    "text": (255, 247, 255),
    "muted": (202, 164, 195),
}


def _font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, filename), size)
    except OSError:
        return ImageFont.load_default()


def _week_key() -> str:
    iso = datetime.now(timezone.utc).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _stable_indices(user_id: int, card_type: str, count: int) -> list[int]:
    digest = hashlib.sha256(
        f"ibeks-card:{card_type}:{user_id}:{_week_key()}".encode("utf-8")
    ).digest()
    return [
        int.from_bytes(digest[offset:offset + 4], "big") % count
        for offset in range(0, count * 4, 4)
    ]


def _stats(user: User, card_type: str) -> dict:
    indices = _stable_indices(user.id, card_type, 5)
    is_female = card_type == "female"
    aura_pool = CCANTIK_AURA if is_female else CTAMPAN_AURA
    tier_pool = CCANTIK_TIER if is_female else CTAMPAN_TIER
    score_digest = hashlib.sha256(
        f"ibeks-score:{card_type}:{user.id}:{_week_key()}".encode("utf-8")
    ).digest()
    score = int.from_bytes(score_digest[:2], "big") % 101
    return {
        "score": score,
        "aura": aura_pool[indices[1] % len(aura_pool)],
        "tier": tier_pool[indices[2] % len(tier_pool)],
        "mental": STATUS_MENTAL[indices[3] % len(STATUS_MENTAL)],
    }


def _name(user: User) -> str:
    name = " ".join(part for part in (user.first_name, user.last_name) if part)
    return name or user.username or "Unknown"


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    """Potong teks panjang dengan ellipsis agar tidak menabrak panel foto."""
    text = str(text)
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return text
    while len(text) > 3 and draw.textbbox((0, 0), text + "…", font=font)[2] > max_width:
        text = text[:-1]
    return text.rstrip() + "…"


def _text(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], value: str, font, fill, shadow=(0, 0, 0)):
    x, y = xy
    draw.text((x + 2, y + 2), value, font=font, fill=shadow)
    draw.text((x, y), value, font=font, fill=fill)


def _draw_background(draw: ImageDraw.ImageDraw, palette: dict) -> None:
    draw.rectangle([0, 0, CARD_WIDTH, CARD_HEIGHT], fill=palette["background"])
    for y in range(0, CARD_HEIGHT, 6):
        draw.line([(0, y), (CARD_WIDTH, y)], fill=palette["panel"], width=1)
    for x in range(0, CARD_WIDTH, 64):
        draw.line([(x, 0), (x, CARD_HEIGHT)], fill=palette["accent_dim"], width=1)
    # Angular decorative panels inspired by the supplied reference.
    draw.polygon(
        [(0, 0), (450, 0), (520, 130), (0, 250)],
        fill=palette["panel"],
    )
    draw.polygon(
        [(1280, 720), (850, 720), (790, 600), (1280, 470)],
        fill=palette["panel"],
    )


def _draw_frame(draw: ImageDraw.ImageDraw, palette: dict) -> None:
    margin = 22
    draw.rounded_rectangle(
        [margin, margin, CARD_WIDTH - margin, CARD_HEIGHT - margin],
        radius=18,
        outline=palette["accent"],
        width=3,
    )
    draw.rounded_rectangle(
        [38, 38, CARD_WIDTH - 38, CARD_HEIGHT - 38],
        radius=12,
        outline=palette["accent_dim"],
        width=1,
    )
    # Corner brackets.
    length = 54
    width = 5
    corners = (
        ((48, 118), (48, 48), (118, 48)),
        ((CARD_WIDTH - 118, 48), (CARD_WIDTH - 48, 48), (CARD_WIDTH - 48, 118)),
        ((48, CARD_HEIGHT - 118), (48, CARD_HEIGHT - 48), (118, CARD_HEIGHT - 48)),
        (
            (CARD_WIDTH - 118, CARD_HEIGHT - 48),
            (CARD_WIDTH - 48, CARD_HEIGHT - 48),
            (CARD_WIDTH - 48, CARD_HEIGHT - 118),
        ),
    )
    for points in corners:
        draw.line(points, fill=palette["accent"], width=width)


def _draw_progress(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    percent: int,
    palette: dict,
) -> None:
    height = 14
    draw.rounded_rectangle(
        [x, y, x + width, y + height],
        radius=7,
        fill=palette["background"],
        outline=palette["accent_dim"],
        width=2,
    )
    filled = max(0, int(width * percent / 100))
    if filled:
        draw.rounded_rectangle(
            [x, y, x + filled, y + height],
            radius=7,
            fill=palette["accent"],
        )
        draw.ellipse(
            [x + filled - 4, y + 3, x + filled + 4, y + 11],
            fill=palette["text"],
        )


def _crop_square(image: Image.Image, size: int) -> Image.Image:
    image = image.convert("RGB")
    side = min(image.width, image.height)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    return image.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")


def _circular_avatar(image: Image.Image, size: int) -> Image.Image:
    image = _crop_square(image, size)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)
    return result


def _default_avatar(size: int, palette: dict, user: User) -> Image.Image:
    avatar = Image.new("RGBA", (size, size), palette["panel_alt"] + (255,))
    draw = ImageDraw.Draw(avatar)
    draw.ellipse([0, 0, size - 1, size - 1], fill=palette["panel_alt"], outline=palette["accent"], width=5)
    draw.ellipse(
        [size * 0.35, size * 0.18, size * 0.65, size * 0.52],
        fill=palette["accent_alt"],
    )
    draw.ellipse(
        [size * 0.16, size * 0.52, size * 0.84, size * 1.14],
        fill=palette["accent"],
    )
    initials = (_name(user)[:2] or "UB").upper()
    font = _font("DejaVuSans-Bold.ttf", max(22, size // 9))
    bbox = draw.textbbox((0, 0), initials, font=font)
    draw.rounded_rectangle(
        [size * 0.30, size * 0.72, size * 0.70, size * 0.90],
        radius=12,
        fill=palette["background"],
    )
    draw.text(
        ((size - (bbox[2] - bbox[0])) // 2, size * 0.735),
        initials,
        font=font,
        fill=palette["text"],
    )
    return avatar


async def _profile_photo(client: Client, user: User) -> Optional[Image.Image]:
    try:
        if not user.photo:
            return None
        downloaded = await client.download_media(user.photo.big_file_id, in_memory=True)
        if downloaded is None:
            return None
        if isinstance(downloaded, bytes):
            return Image.open(io.BytesIO(downloaded))
        if hasattr(downloaded, "getvalue"):
            return Image.open(io.BytesIO(downloaded.getvalue()))
        if hasattr(downloaded, "read"):
            return Image.open(downloaded)
    except Exception as exc:
        log.warning(f"[FunCard] Gagal download foto profil: {exc}")
    return None


def _draw_code(draw: ImageDraw.ImageDraw, x: int, y: int, user_id: int, palette: dict) -> None:
    """Barcode dekoratif ringan agar kartu tetap mandiri dari barcode renderer."""
    seed = hashlib.sha256(str(user_id).encode("utf-8")).digest()
    cursor = x
    for byte in seed[:28]:
        bar_width = 2 + (byte % 5)
        bar_height = 48 - (byte % 12)
        draw.rectangle([cursor, y + (48 - bar_height), cursor + bar_width, y + 48], fill=palette["text"])
        cursor += bar_width + 3
        if cursor > x + 280:
            break
    draw.rectangle([x - 10, y - 10, x + 290, y + 58], outline=palette["accent_dim"], width=2)


def _draw_qr(draw: ImageDraw.ImageDraw, x: int, y: int, user_id: int, palette: dict) -> None:
    qr = qrcode.QRCode(version=1, box_size=3, border=1)
    qr.add_data(f"IBEKS:{user_id}")
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    image = image.resize((86, 86), Image.Resampling.NEAREST)
    draw.rectangle([x - 6, y - 6, x + 92, y + 92], fill="white", outline=palette["accent"], width=2)
    draw._image.paste(image, (x, y))


def _field_value(
    draw: ImageDraw.ImageDraw,
    label: str,
    value: str,
    y: int,
    palette: dict,
    value_font,
    label_font,
    progress: Optional[int] = None,
) -> None:
    x_label = 70
    x_value = 292
    draw.line([(70, y + 41), (690, y + 41)], fill=palette["accent_dim"], width=1)
    draw.rounded_rectangle([70, y + 3, 92, y + 25], radius=4, fill=palette["accent"])
    _text(draw, (112, y), label, label_font, palette["accent"])
    _text(draw, (260, y), ":", label_font, palette["text"])
    if progress is None:
        value = _fit_text(draw, value, value_font, 410)
        _text(draw, (x_value, y), value, value_font, palette["text"])
    else:
        _text(draw, (x_value, y), f"{progress}%", value_font, palette["text"])
        _draw_progress(draw, x_value + 78, y + 8, 230, progress, palette)


async def generate_fun_card(client: Client, user: User, card_type: str) -> io.BytesIO:
    """Buat kartu pria atau wanita dengan nilai mingguan yang stabil."""
    if card_type not in {"male", "female"}:
        raise ValueError("card_type harus 'male' atau 'female'")

    palette = MALE_PALETTE if card_type == "male" else FEMALE_PALETTE
    stats = _stats(user, card_type)
    name = _name(user)
    username = f"@{user.username}" if user.username else "N/A"
    stat_label = "KETAMPANAN" if card_type == "male" else "KECANTIKAN"
    card_title = "ID CARD / MALE" if card_type == "male" else "ID CARD / FEMALE"
    badge = "2ND GENERATION" if card_type == "male" else "NEON EDITION"

    image = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), palette["background"] + (255,))
    draw = ImageDraw.Draw(image)
    _draw_background(draw, palette)
    _draw_frame(draw, palette)

    font_header = _font("DejaVuSans-Bold.ttf", 24)
    font_title = _font("DejaVuSans-Bold.ttf", 38)
    font_label = _font("DejaVuSans-Bold.ttf", 17)
    font_value = _font("DejaVuSans.ttf", 19)
    font_small = _font("DejaVuSans.ttf", 15)

    _text(draw, (70, 56), card_title, font_header, palette["text"])
    _text(draw, (560, 54), "IBEKS // PERSONAL IDENTITY SYSTEM", font_small, palette["muted"])
    draw.rounded_rectangle([70, 112, 285, 151], radius=18, fill=palette["accent"])
    _text(draw, (96, 120), "TRAINER PROFILE", _font("DejaVuSans-Bold.ttf", 16), palette["background"])
    draw.line([(305, 132), (530, 132)], fill=palette["accent"], width=4)
    draw.line([(320, 143), (470, 143)], fill=palette["accent_alt"], width=2)
    _text(draw, (70, 170), "PERSONAL DATA", _font("DejaVuSans-Bold.ttf", 15), palette["accent_alt"])

    fields = (
        ("NAMA", name, None),
        ("USERNAME", username, None),
        ("USER ID", str(user.id), None),
        (stat_label, "", stats["score"]),
        ("AURA", stats["aura"], None),
        ("TIER", stats["tier"], None),
        ("STATUS MENTAL", stats["mental"], None),
    )
    for index, (label, value, progress) in enumerate(fields):
        _field_value(draw, label, value, 208 + index * 57, palette, font_value, font_label, progress)

    # Photo panel on the right.
    center_x, center_y, radius = 965, 355, 190
    draw.rounded_rectangle([730, 145, 1190, 570], radius=32, fill=palette["panel"], outline=palette["accent_dim"], width=2)
    for offset in (18, 10, 4):
        draw.ellipse(
            [center_x - radius - offset, center_y - radius - offset, center_x + radius + offset, center_y + radius + offset],
            outline=palette["accent_dim"],
            width=3,
        )
    draw.ellipse(
        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
        outline=palette["accent"],
        width=6,
    )

    profile = await _profile_photo(client, user)
    if profile is None:
        profile_circle = _default_avatar(radius * 2 - 26, palette, user)
    else:
        profile_circle = _circular_avatar(profile, radius * 2 - 26)
    photo_size = radius * 2 - 26
    image.paste(
        profile_circle,
        (center_x - photo_size // 2, center_y - photo_size // 2),
        profile_circle,
    )
    draw = ImageDraw.Draw(image)
    _text(draw, (775, 178), "BIOMETRIC PHOTO", font_small, palette["muted"])
    _text(draw, (805, 528), badge, _font("DejaVuSans-Bold.ttf", 15), palette["accent_alt"])

    # Footer, code and QR.
    draw.line([(70, 625), (1190, 625)], fill=palette["accent_dim"], width=2)
    _text(draw, (70, 646), "DO NOT MOCK THE ORDINARY.", font_small, palette["muted"])
    _text(draw, (510, 642), "IBEKS", _font("DejaVuSans-Bold.ttf", 32), palette["text"])
    _text(draw, (585, 678), "USERBOT", _font("DejaVuSans-Bold.ttf", 13), palette["accent_alt"])
    _draw_code(draw, 760, 640, user.id, palette)
    _draw_qr(draw, 1090, 638, user.id, palette)

    result = io.BytesIO()
    image.convert("RGB").save(result, format="PNG", optimize=True)
    result.seek(0)
    return result
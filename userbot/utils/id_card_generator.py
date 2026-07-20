"""
IBEKS USERBOT - ID Card Generator
Membuat kartu identitas futuristik hitam-hijau neon untuk command .id.
Layout terinspirasi dari kartu ID game/esports dengan panel kiri,
foto profil lingkaran besar di kanan, HUD lines, barcode, dan QR.
"""

import io
import os
import random
from datetime import datetime
from typing import Optional, Tuple

import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pyrogram import Client
from pyrogram.types import User

from config import BOT_NAME
from utils.fun_data import CTAMPAN_AURA, CTAMPAN_TIER, CCANTIK_AURA, CCANTIK_TIER
from utils.id_data import STATUS_MENTAL
from utils.logger import log


# ── Konfigurasi dimensi & warna ───────────────────────────────────────────────

CARD_WIDTH = 1280
CARD_HEIGHT = 720

COLORS = {
    "bg": (5, 5, 5),
    "bg_alt": (10, 15, 10),
    "neon": (57, 255, 20),
    "neon_dim": (30, 140, 15),
    "white": (255, 255, 255),
    "cyan": (0, 240, 255),
    "yellow": (240, 255, 0),
    "gray": (120, 120, 120),
    "dark_panel": (15, 20, 15, 180),
    "redacted": (80, 80, 80),
}

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load font TrueType dengan fallback ke default."""
    path = os.path.join(FONT_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _current_week_seed() -> int:
    """Seed unik untuk minggu ISO saat ini."""
    iso = datetime.now().isocalendar()
    return iso.year * 100 + iso.week


def _generate_stats(user: User) -> dict:
    """Generate nilai deterministik untuk ID card."""
    base_seed = user.id * 100000 + _current_week_seed()
    rng = random.Random(base_seed)

    tampan_pct = rng.randint(50, 100)
    cantik_pct = rng.randint(50, 100)
    aura = rng.choice(CTAMPAN_AURA)
    tier = rng.choice(CTAMPAN_TIER)
    mental = rng.choice(STATUS_MENTAL)

    return {
        "tampan": tampan_pct,
        "cantik": cantik_pct,
        "aura": aura,
        "tier": tier,
        "mental": mental,
    }


async def _fetch_profile_photo(client: Client, user: User) -> Optional[Image.Image]:
    """Download foto profil user dari Telegram."""
    try:
        if not user.photo:
            return None
        photo_io = await client.download_media(user.photo.big_file_id, in_memory=True)
        if photo_io is None:
            return None
        if isinstance(photo_io, bytes):
            return Image.open(io.BytesIO(photo_io))
        if hasattr(photo_io, "getvalue"):
            return Image.open(io.BytesIO(photo_io.getvalue()))
        if hasattr(photo_io, "read"):
            return Image.open(photo_io)
        return None
    except Exception as exc:
        log.warning(f"[IDCard] Gagal download foto profil: {exc}")
        return None


def _create_placeholder(size: int) -> Image.Image:
    """Buat placeholder lingkaran untuk user tanpa foto."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size, size], fill=(25, 30, 25, 255))
    draw.ellipse(
        [size * 0.3, size * 0.2, size * 0.7, size * 0.6],
        fill=(57, 255, 20, 80),
    )
    draw.ellipse(
        [size * 0.2, size * 0.65, size * 0.8, size * 1.1],
        fill=(57, 255, 20, 80),
    )
    return img


def _circular_mask(image: Image.Image, size: int) -> Image.Image:
    """Crop image menjadi lingkaran dengan ukuran tertentu."""
    image = image.convert("RGBA")
    image.thumbnail((size, size), Image.Resampling.LANCZOS)
    
    # Buat canvas persegi dengan ukuran size
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - image.width) // 2
    y = (size - image.height) // 2
    canvas.paste(image, (x, y))
    
    # Mask lingkaran
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([0, 0, size, size], fill=255)
    
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(canvas, (0, 0), mask)
    return result


def _draw_glow_ring(
    draw: ImageDraw.ImageDraw,
    center: Tuple[int, int],
    radius: int,
    color: Tuple[int, int, int],
    width: int = 4,
) -> None:
    """Gambar lingkaran dengan glow effect."""
    bbox = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
    # Outer glow ring
    for i in range(8, 0, -2):
        alpha_ring = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 0))
        ring_draw = ImageDraw.Draw(alpha_ring)
        ring_draw.ellipse(
            [bbox[0] - i, bbox[1] - i, bbox[2] + i, bbox[3] + i],
            outline=(*color, 40 - i * 4),
            width=width + i // 2,
        )
    # Main ring
    draw.ellipse(bbox, outline=color, width=width)


def _draw_corner_brackets(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    color: Tuple[int, int, int],
    length: int = 40,
    width: int = 3,
) -> None:
    """Gambar bracket sudut HUD."""
    # Top-left
    draw.line([(x, y + length), (x, y), (x + length, y)], fill=color, width=width)
    # Top-right
    draw.line([(x + w - length, y), (x + w, y), (x + w, y + length)], fill=color, width=width)
    # Bottom-left
    draw.line([(x, y + h - length), (x, y + h), (x + length, y + h)], fill=color, width=width)
    # Bottom-right
    draw.line([(x + w - length, y + h), (x + w, y + h), (x + w, y + h - length)], fill=color, width=width)


def _draw_progress_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    percent: int,
    color: Tuple[int, int, int],
) -> None:
    """Gambar progress bar sederhana."""
    filled = int(width * max(0, min(100, percent)) / 100)
    draw.rounded_rectangle([x, y, x + width, y + height], radius=height // 2, outline=(60, 60, 60), width=2)
    if filled > 0:
        draw.rounded_rectangle([x, y, x + filled, y + height], radius=height // 2, fill=color)


def _draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    text: str,
    pos: Tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    shadow_color: Tuple[int, int, int] = (0, 0, 0),
    shadow_offset: Tuple[int, int] = (2, 2),
) -> None:
    """Gambar teks dengan bayangan tipis."""
    x, y = pos
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill)


def _generate_barcode(user_id: int) -> Image.Image:
    """Generate barcode Code128 dari user ID."""
    try:
        writer = ImageWriter()
        writer.set_options({
            "write_text": False,
            "module_height": 12,
            "module_width": 0.25,
            "quiet_zone": 2,
        })
        code = Code128(str(user_id), writer=writer)
        buffer = io.BytesIO()
        code.write(buffer)
        buffer.seek(0)
        return Image.open(buffer).convert("RGBA")
    except Exception as exc:
        log.warning(f"[IDCard] Gagal generate barcode: {exc}")
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))


def _generate_qr(user_id: int) -> Image.Image:
    """Generate QR code dari user ID."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(str(user_id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
        return img
    except Exception as exc:
        log.warning(f"[IDCard] Gagal generate QR: {exc}")
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))


def _draw_hexagon_pattern(draw: ImageDraw.ImageDraw, color: Tuple[int, int, int]) -> None:
    """Gambar pattern hexagon tipis sebagai background."""
    import math
    size = 40
    for row in range(-1, CARD_HEIGHT // size + 2):
        for col in range(-1, CARD_WIDTH // size + 2):
            x = col * size * 1.5
            y = row * size * math.sqrt(3) + (col % 2) * size * math.sqrt(3) / 2
            # Hanya gambar titik-titik sudut untuk efek subtle
            for angle in range(0, 360, 60):
                px = x + size * math.cos(math.radians(angle))
                py = y + size * math.sin(math.radians(angle))
                if 0 <= px <= CARD_WIDTH and 0 <= py <= CARD_HEIGHT:
                    draw.ellipse([px - 1, py - 1, px + 1, py + 1], fill=color)


def _draw_hud_lines(draw: ImageDraw.ImageDraw) -> None:
    """Gambar garis-garis HUD futuristik."""
    # Garis horizontal tipis di bawah header
    draw.line([(60, 110), (1220, 110)], fill=COLORS["neon_dim"], width=1)
    # Garis vertikal pemisah kiri-kanan
    draw.line([(720, 150), (720, 620)], fill=COLORS["neon_dim"], width=1)
    # Titik-titik dekoratif
    for x in range(60, 1221, 40):
        draw.ellipse([x - 1, 105 - 1, x + 1, 105 + 1], fill=COLORS["neon_dim"])


def _draw_logo(draw: ImageDraw.ImageDraw, cx: int, cy: int, font: ImageFont.FreeTypeFont) -> None:
    """Gambar logo teks IBEKS USERBOT."""
    text = "IBEKS"
    sub = "USERBOT"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    _draw_text_with_shadow(draw, text, (cx - text_w // 2, cy - 30), font, COLORS["white"])
    
    sub_font = _load_font("DejaVuSans-Bold.ttf", 18)
    bbox_sub = draw.textbbox((0, 0), sub, font=sub_font)
    sub_w = bbox_sub[2] - bbox_sub[0]
    _draw_text_with_shadow(draw, sub, (cx - sub_w // 2, cy + 10), sub_font, COLORS["neon"])

    # Icon skull kecil
    draw.ellipse([cx - 8, cy - 60, cx + 8, cy - 44], outline=COLORS["neon"], width=2)
    draw.ellipse([cx - 5, cy - 56, cx - 2, cy - 52], fill=COLORS["neon"])
    draw.ellipse([cx + 2, cy - 56, cx + 5, cy - 52], fill=COLORS["neon"])
    draw.rectangle([cx - 3, cy - 48, cx + 3, cy - 44], fill=COLORS["neon"])


async def generate_id_card(client: Client, user: User) -> io.BytesIO:
    """
    Generate kartu ID futuristik dan kembalikan sebagai BytesIO PNG.
    """
    stats = _generate_stats(user)
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Unknown"
    username = f"@{user.username}" if user.username else "N/A"
    user_id_str = str(user.id)

    # Load fonts
    font_title = _load_font("DejaVuSans-Bold.ttf", 38)
    font_header = _load_font("DejaVuSans-Bold.ttf", 18)
    font_label = _load_font("DejaVuSans-Bold.ttf", 20)
    font_value = _load_font("DejaVuSans.ttf", 20)
    font_badge = _load_font("DejaVuSans-Bold.ttf", 16)
    font_small = _load_font("DejaVuSans.ttf", 14)

    # Base image
    img = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    # Background gradient radial
    for r in range(max(CARD_WIDTH, CARD_HEIGHT) // 2, 0, -2):
        alpha = int(20 * (r / (max(CARD_WIDTH, CARD_HEIGHT) // 2)))
        draw.ellipse(
            [CARD_WIDTH // 2 - r, CARD_HEIGHT // 2 - r, CARD_WIDTH // 2 + r, CARD_HEIGHT // 2 + r],
            fill=(*COLORS["bg_alt"], alpha),
        )

    # Hexagon pattern
    _draw_hexagon_pattern(draw, COLORS["neon_dim"])

    # Main frame border
    _draw_corner_brackets(draw, 30, 25, CARD_WIDTH - 60, CARD_HEIGHT - 50, COLORS["neon"], length=70, width=3)
    draw.rectangle([40, 35, CARD_WIDTH - 40, CARD_HEIGHT - 35], outline=COLORS["neon_dim"], width=1)

    # Header
    _draw_text_with_shadow(draw, "ID CARD", (60, 50), font_header, COLORS["neon"])
    header_text = "IBEKS USERBOT OFFICIAL ID"
    bbox = draw.textbbox((0, 0), header_text, font=font_header)
    header_w = bbox[2] - bbox[0]
    _draw_text_with_shadow(draw, header_text, ((CARD_WIDTH - header_w) // 2, 50), font_header, COLORS["white"])

    # HUD lines
    _draw_hud_lines(draw)

    # Badge
    badge_text = "IBEKS USER"
    badge_w, badge_h = 160, 30
    badge_x, badge_y = 60, 150
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=8, fill=COLORS["neon"])
    bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        (badge_x + (badge_w - text_w) // 2, badge_y + (badge_h - text_h) // 2 - 2),
        badge_text,
        font=font_badge,
        fill=COLORS["bg"],
    )

    # Info panel fields
    fields = [
        ("NAMA", name),
        ("USERNAME", username),
        ("USER ID", user_id_str),
        ("TAMPAN", f"{stats['tampan']}%"),
        ("CANTIK", f"{stats['cantik']}%"),
        ("AURA", stats["aura"]),
        ("TIER", stats["tier"]),
        ("STATUS MENTAL", stats["mental"]),
    ]

    start_y = 210
    line_height = 50
    label_x = 60
    value_x = 220
    progress_width = 220

    for i, (label, value) in enumerate(fields):
        y = start_y + i * line_height
        # Icon square
        draw.rectangle([label_x, y, label_x + 22, y + 22], outline=COLORS["neon"], width=2)
        # Label
        _draw_text_with_shadow(draw, label, (label_x + 32, y), font_label, COLORS["neon"])
        _draw_text_with_shadow(draw, ":", (label_x + 180, y), font_label, COLORS["white"])

        if label in ("TAMPAN", "CANTIK"):
            _draw_text_with_shadow(draw, value, (value_x, y), font_value, COLORS["white"])
            pct = int(value.replace("%", ""))
            _draw_progress_bar(draw, value_x + 70, y + 8, progress_width, 12, pct, COLORS["neon"])
        else:
            # Truncate value kalau terlalu panjang
            max_width = 480
            bbox = draw.textbbox((0, 0), value, font=font_value)
            text_w = bbox[2] - bbox[0]
            if text_w > max_width:
                while text_w > max_width and len(value) > 3:
                    value = value[:-1]
                    bbox = draw.textbbox((0, 0), value + "...", font=font_value)
                    text_w = bbox[2] - bbox[0]
                value += "..."
            _draw_text_with_shadow(draw, value, (value_x, y), font_value, COLORS["white"])

    # Profile photo circle
    circle_center = (980, 330)
    circle_radius = 180

    # Outer glow
    glow_layer = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    for offset in range(25, 0, -5):
        glow_draw.ellipse(
            [
                circle_center[0] - circle_radius - offset,
                circle_center[1] - circle_radius - offset,
                circle_center[0] + circle_radius + offset,
                circle_center[1] + circle_radius + offset,
            ],
            outline=(*COLORS["neon"], 20),
            width=6,
        )
    img = Image.alpha_composite(img, glow_layer)
    draw = ImageDraw.Draw(img)

    # Main ring
    draw.ellipse(
        [
            circle_center[0] - circle_radius,
            circle_center[1] - circle_radius,
            circle_center[0] + circle_radius,
            circle_center[1] + circle_radius,
        ],
        outline=COLORS["neon"],
        width=5,
    )
    # Inner ring
    draw.ellipse(
        [
            circle_center[0] - circle_radius + 15,
            circle_center[1] - circle_radius + 15,
            circle_center[0] + circle_radius - 15,
            circle_center[1] + circle_radius - 15,
        ],
        outline=COLORS["neon_dim"],
        width=2,
    )

    # Profile photo
    profile_img = await _fetch_profile_photo(client, user)
    if profile_img is None:
        profile_img = _create_placeholder(circle_radius * 2 - 30)
    profile_circle = _circular_mask(profile_img, circle_radius * 2 - 30)
    img.paste(
        profile_circle,
        (
            circle_center[0] - (circle_radius * 2 - 30) // 2,
            circle_center[1] - (circle_radius * 2 - 30) // 2,
        ),
        profile_circle,
    )

    # Bottom section: Barcode & QR
    barcode_img = _generate_barcode(user.id)
    barcode_img = barcode_img.resize((260, 60), Image.Resampling.LANCZOS)
    img.paste(barcode_img, (950, 580), barcode_img)
    _draw_text_with_shadow(draw, "IBEKS USERBOT OFFICIAL ID", (990, 650), font_small, COLORS["gray"])

    qr_img = _generate_qr(user.id)
    qr_img = qr_img.resize((90, 90), Image.Resampling.LANCZOS)
    # Tambahkan border putih tipis
    qr_with_border = Image.new("RGBA", (100, 100), COLORS["white"])
    qr_with_border.paste(qr_img, (5, 5))
    img.paste(qr_with_border, (1180, 560), qr_with_border)

    # Logo bottom center
    _draw_logo(draw, 450, 630, font_title)

    # Convert to RGB dan save ke BytesIO
    final = img.convert("RGB")
    buffer = io.BytesIO()
    final.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer

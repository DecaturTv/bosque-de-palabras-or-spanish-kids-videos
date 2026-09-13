"""Frame rendering.

Real illustrated assets (Chispa sprites, topic icons, clearing
backgrounds) don't exist yet — assets/mascot, assets/icons,
assets/backgrounds are empty placeholders. These functions draw
programmatic vector-style stand-ins from config/style.yaml's palette
so the pipeline produces a real video today. When a lesson's
image_asset/background path actually exists on disk, it is loaded
and used instead — no pipeline changes needed to swap in real art
later.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoClip

from bosque.style import load_style

REPO_ROOT = Path(__file__).resolve().parents[2]
VIDEO_SIZE = (1280, 720)  # proxy resolution; style guide px values assume 1080p scaling
FPS = 24

_FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
_FONT_BOLD = _FONT_DIR / "DejaVuSans-Bold.ttf"
_FONT_REGULAR = _FONT_DIR / "DejaVuSans.ttf"


def _font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    path = _FONT_BOLD if bold else _FONT_REGULAR
    return ImageFont.truetype(str(path), size)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def _palette() -> dict[str, tuple[int, int, int]]:
    p = load_style()["palette"]
    return {k: _hex(v) for k, v in p.items() if k != "avoid"}


def _rounded_rect(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=0):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _text_centered(draw, xy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = xy
    draw.text((x - w / 2 - bbox[0], y - h / 2 - bbox[1]), text, font=font, fill=fill)


def _fit_font(draw, text: str, max_width: float, start_size: int, min_size: int = 14) -> ImageFont.FreeTypeFont:
    size = start_size
    while size > min_size:
        font = _font(True, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 2
    return _font(True, min_size)


def background_frame(tier: str, clearing: str, background_asset: str | None = None) -> Image.Image:
    asset_path = REPO_ROOT / background_asset if background_asset else None
    if asset_path and asset_path.exists():
        return Image.open(asset_path).convert("RGB").resize(VIDEO_SIZE)

    pal = _palette()
    w, h = VIDEO_SIZE
    img = Image.new("RGB", VIDEO_SIZE, pal["neutral"])
    draw = ImageDraw.Draw(img)
    # sky band
    draw.rectangle([0, 0, w, h * 0.55], fill=pal["neutral"])
    # forest ground
    draw.rectangle([0, h * 0.55, w, h], fill=pal["secondary"])
    # simple rounded "tree" foliage clumps along the tree line, deterministic per clearing
    rng_seed = sum(ord(c) for c in clearing)
    for i in range(8):
        cx = (i * 173 + rng_seed * 7) % w
        cy = h * 0.55 - 10
        r = 40 + (i * 37 + rng_seed) % 30
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["secondary"])
    draw.text((24, 20), clearing, font=_font(True, 28), fill=pal["primary"])
    return img


def draw_chispa(img: Image.Image, bounce_phase: float) -> Image.Image:
    """Small orange-and-white fox, bottom-left, subtle idle bounce."""
    pal = _palette()
    outline = (60, 60, 60)
    img = img.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    cx, cy = int(w * 0.13), int(h * 0.78 + 6 * math.sin(bounce_phase))
    scale = 95
    head_cx, head_cy, head_r = cx, cy - scale * 0.75, scale * 0.5

    # backpack (behind everything)
    draw.rounded_rectangle(
        [cx - scale * 0.95, cy - scale * 0.15, cx - scale * 0.35, cy + scale * 0.55],
        radius=14,
        fill=pal["neutral"],
        outline=outline,
        width=4,
    )

    # ears — drawn before the head so the head circle covers their base,
    # leaving oversized round tips visible above/beside the head
    for dx in (-1, 1):
        ex = head_cx + dx * head_r * 0.8
        ey = head_cy - head_r * 0.85
        r = head_r * 0.55
        draw.ellipse([ex - r, ey - r, ex + r, ey + r], fill=pal["primary"], outline=outline, width=4)
        r2 = r * 0.5
        draw.ellipse([ex - r2, ey - r2, ex + r2, ey + r2], fill=pal["neutral"])

    # body
    draw.ellipse(
        [cx - scale * 0.55, cy - scale * 0.35, cx + scale * 0.55, cy + scale * 0.75],
        fill=pal["primary"],
        outline=outline,
        width=5,
    )
    # cream belly
    draw.ellipse(
        [cx - scale * 0.28, cy - scale * 0.05, cx + scale * 0.28, cy + scale * 0.7],
        fill=pal["neutral"],
    )

    # head
    draw.ellipse(
        [head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r],
        fill=pal["primary"],
        outline=outline,
        width=5,
    )
    # cream muzzle
    draw.ellipse(
        [head_cx - head_r * 0.55, head_cy, head_cx + head_r * 0.55, head_cy + head_r * 0.75],
        fill=pal["neutral"],
    )
    # eyes
    for dx in (-1, 1):
        ex = head_cx + dx * head_r * 0.4
        ey = head_cy - head_r * 0.05
        draw.ellipse([ex - 7, ey - 7, ex + 7, ey + 7], fill=(40, 30, 20))
    # nose
    nx, ny = head_cx, head_cy + head_r * 0.35
    draw.ellipse([nx - 7, ny - 6, nx + 7, ny + 6], fill=(40, 30, 20))
    return img


def vocab_card_frame(
    background: Image.Image,
    spanish: str,
    english: str,
    phonetic_hint: str | None,
    accent_index: int,
) -> Image.Image:
    pal = _palette()
    img = background.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    card_box = [w * 0.28, h * 0.18, w * 0.95, h * 0.55]
    _rounded_rect(draw, card_box, 28, fill=pal["neutral"], outline=pal["primary"], width=5)

    # placeholder "icon": colored circle with first letter, standing in
    # for the real illustration referenced by image_asset
    accent_colors = [pal["primary"], pal["secondary"], pal["accent"]]
    circle_color = accent_colors[accent_index % len(accent_colors)]
    icon_cx, icon_cy, icon_r = (card_box[0] + 70), (card_box[1] + 70), 50
    draw.ellipse(
        [icon_cx - icon_r, icon_cy - icon_r, icon_cx + icon_r, icon_cy + icon_r],
        fill=circle_color,
    )
    _text_centered(draw, (icon_cx, icon_cy), spanish[0].upper(), _font(True, 44), pal["neutral"])

    text_x = icon_cx + icon_r + 40
    label = spanish if not phonetic_hint else f"{spanish}  ({phonetic_hint})"
    max_width = card_box[2] - text_x - 20
    draw.text((text_x, card_box[1] + 30), label, font=_fit_font(draw, label, max_width, 46), fill=pal["primary"])
    draw.text(
        (text_x, card_box[1] + 95), english, font=_fit_font(draw, english, max_width, 32), fill=(120, 120, 120)
    )
    return img


def flash_object_frame(background: Image.Image, label: str, color_index: int) -> Image.Image:
    """One matched-object flash during a song line."""
    pal = _palette()
    img = background.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    accent_colors = [pal["primary"], pal["secondary"], pal["accent"]]
    color = accent_colors[color_index % len(accent_colors)]
    cx, cy, r = w * 0.6, h * 0.35, 90
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline=(60, 60, 60), width=5)
    font = _fit_font(draw, label, r * 1.7, 34)
    _text_centered(draw, (cx, cy), label, font, pal["neutral"])
    return img


def all_objects_flash_frame(background: Image.Image, labels: list[str]) -> Image.Image:
    pal = _palette()
    img = background.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    accent_colors = [pal["primary"], pal["secondary"], pal["accent"]]
    n = len(labels)
    spacing = w * 0.7 / max(n, 1)
    start_x = w * 0.5 - spacing * (n - 1) / 2
    for i, label in enumerate(labels):
        cx = start_x + i * spacing
        cy = h * 0.35
        r = 60
        color = accent_colors[i % len(accent_colors)]
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline=(60, 60, 60), width=4)
        font = _fit_font(draw, label, r * 1.7, 24)
        _text_centered(draw, (cx, cy), label, font, pal["neutral"])
    return img


def text_card_frame(background: Image.Image, lines_es: list[str], line_en: str | None = None) -> Image.Image:
    pal = _palette()
    img = background.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    box = [w * 0.24, h * 0.62, w * 0.95, h * 0.95]
    _rounded_rect(draw, box, 24, fill=pal["neutral"], outline=pal["primary"], width=5)
    max_width = (box[2] - box[0]) - 48
    y = box[1] + 20
    for line in lines_es[:2]:
        font = _fit_font(draw, line, max_width, 34, min_size=20)
        draw.text((box[0] + 24, y), line, font=font, fill=pal["primary"])
        y += font.size + 12
    if line_en:
        en_font = _fit_font(draw, line_en, max_width, 26, min_size=16)
        draw.text((box[0] + 24, y + 6), line_en, font=en_font, fill=(120, 120, 120))
    return img


def quiz_frame(
    background: Image.Image,
    prompt_es: str,
    options: list[str],
    correct: str | None = None,
    reveal: bool = False,
) -> Image.Image:
    pal = _palette()
    img = background.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    draw.text((w * 0.08, h * 0.1), prompt_es, font=_font(True, 40), fill=pal["primary"])

    n = len(options)
    box_w, box_h, gap = 260, 90, 30
    total_w = n * box_w + (n - 1) * gap
    start_x = (w - total_w) / 2
    y = h * 0.55
    for i, opt in enumerate(options):
        x = start_x + i * (box_w + gap)
        box = [x, y, x + box_w, y + box_h]
        is_correct = reveal and opt == correct
        fill = pal["accent"] if is_correct else pal["neutral"]
        _rounded_rect(draw, box, 18, fill=fill, outline=pal["primary"], width=4)
        font = _fit_font(draw, opt, box_w * 0.85, 30)
        _text_centered(draw, ((x + x + box_w) / 2, (y + y + box_h) / 2), opt, font, pal["primary"])
        if is_correct:
            _draw_starburst(draw, ((x + x + box_w) / 2, y - 20), 40, pal["accent"])
    return img


def _draw_starburst(draw: ImageDraw.ImageDraw, center, radius, color):
    cx, cy = center
    for i in range(8):
        angle = i * math.pi / 4
        x2, y2 = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
        draw.line([cx, cy, x2, y2], fill=color, width=5)


def ease_out_back(t: float) -> float:
    """0..1 -> 0..1 with a slight overshoot, per the style guide's pop-in easing."""
    c1, c3 = 1.70158, 2.70158
    t = min(max(t, 0.0), 1.0)
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def pop_in_clip(frame: Image.Image, duration: float, pop_duration: float = 0.35) -> VideoClip:
    """Show `frame`, scaling in 0->1 (with ease-out-back overshoot) over
    `pop_duration`, then holding static for the rest of `duration`.
    """
    frame = frame.convert("RGB")
    w, h = frame.size
    fill = _palette()["neutral"]
    arr_full = np.array(frame)

    def make_frame(t: float):
        if t >= pop_duration:
            return arr_full
        s = max(ease_out_back(t / pop_duration), 0.05)
        new_w, new_h = max(1, round(w * s)), max(1, round(h * s))
        resized = frame.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGB", (w, h), fill)
        canvas.paste(resized, ((w - new_w) // 2, (h - new_h) // 2))
        return np.array(canvas)

    return VideoClip(make_frame, duration=duration).with_fps(FPS)


def static_clip(image: Image.Image, duration: float) -> VideoClip:
    arr = np.array(image.convert("RGB"))
    return VideoClip(lambda t: arr, duration=duration).with_fps(FPS)


def bounce_clip(build_frame_at_phase, duration: float) -> VideoClip:
    """build_frame_at_phase(phase: float) -> PIL.Image, phase advances
    over time to drive Chispa's idle bounce loop.
    """

    def make_frame(t: float):
        phase = t * 2 * math.pi / 1.4  # ~1.4s bounce cycle
        return np.array(build_frame_at_phase(phase).convert("RGB"))

    return VideoClip(make_frame, duration=duration).with_fps(FPS)

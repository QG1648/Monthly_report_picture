from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from decoration_renderer import draw_dots, draw_heart, draw_leaf, draw_sparkle, draw_star, draw_tape, draw_wave_line
from utils import COLORS, jittered_polygon, project_root, rotate_layer, text_bbox


@dataclass
class TextBoxInfo:
    text: str
    bbox: tuple[int, int, int, int]
    text_bbox: tuple[int, int, int, int]
    warning: str | None = None


def find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: list[Path] = []
    root = project_root()
    candidates.extend(sorted((root / "fonts").glob("*.ttf")))
    candidates.extend(sorted((root / "fonts").glob("*.otf")))
    win = Path("C:/Windows/Fonts")
    if bold:
        candidates.extend([win / "msyhbd.ttc", win / "simhei.ttf", win / "msyh.ttc", win / "simsun.ttc"])
    else:
        candidates.extend([win / "msyh.ttc", win / "simhei.ttf", win / "simsun.ttc", win / "simkai.ttf"])
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 2) -> list[str]:
    img = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(img)
    if text_bbox(draw, (0, 0), text, font)[2] <= max_width:
        return [text]

    # Chinese captions read more naturally when two lines have comparable
    # visual widths; avoid leaving one or two orphan characters on line two.
    if max_lines == 2:
        candidates: list[tuple[int, int, list[str]]] = []
        for split_at in range(1, len(text)):
            first, second = text[:split_at], text[split_at:]
            first_w = text_bbox(draw, (0, 0), first, font)[2]
            second_w = text_bbox(draw, (0, 0), second, font)[2]
            if first_w <= max_width and second_w <= max_width:
                orphan_penalty = 10000 if min(len(first), len(second)) < 3 else 0
                candidates.append((orphan_penalty + abs(first_w - second_w), split_at, [first, second]))
        if candidates:
            return min(candidates, key=lambda item: (item[0], item[1]))[2]

    lines: list[str] = []
    current = ""
    for char in text:
        trial = current + char
        if text_bbox(draw, (0, 0), trial, font)[2] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = char
            if len(lines) == max_lines - 1:
                break
    if current:
        rest_start = sum(len(line) for line in lines)
        current = text[rest_start:]
        while text_bbox(draw, (0, 0), current, font)[2] > max_width and len(current) > 1:
            current = current[:-1]
        lines.append(current)
    return lines[:max_lines]


def fit_text(text: str, max_width: int, start_size: int, min_size: int, max_lines: int = 2) -> tuple[ImageFont.ImageFont, list[str], str | None]:
    warning = None
    for size in range(start_size, min_size - 1, -2):
        font = find_font(size)
        lines = wrap_text(text, font, max_width, max_lines)
        if "".join(lines) == text:
            return font, lines, None
    font = find_font(min_size)
    lines = wrap_text(text, font, max_width, max_lines)
    if "".join(lines) != text:
        warning = f"文字过长，已显示可容纳部分: {text}"
    return font, lines, warning


NOTE_STYLES = {
    "note_yellow": "note_torn_yellow",
    "note_blue": "note_blue_lines",
    "note_irregular": "note_warm_heart",
}

PALETTE = {
    "cream_yellow": "#F7E7A9",
    "soft_blue": "#DCECF6",
    "warm_beige": "#F3E7D3",
    "sage": "#E3EDD8",
    "apricot": "#F6E2D1",
    "gray_blue": "#DCE5EA",
    "text": "#425968",
    "text_warm": "#53504A",
}


def render_title(canvas: Image.Image, title: str, child_name: str, month: str, seed: int) -> list[TextBoxInfo]:
    draw = ImageDraw.Draw(canvas, "RGBA")
    rng = random.Random(seed + 11)
    infos: list[TextBoxInfo] = []
    bridge = jittered_polygon(980, 155, 960, 155, rng, jitter=8, steps=10)
    draw.polygon(bridge, fill=(*_rgb(PALETTE["soft_blue"]), 150))
    title_paper = jittered_polygon(105, 82, 1090, 325, rng, jitter=10, steps=11)
    draw.polygon(title_paper, fill=(*_rgb(COLORS["yellow"]), 188))
    draw.line(title_paper + [title_paper[0]], fill=(*_rgb(COLORS["yellow"]), 205), width=3)
    title_font = find_font(108, bold=True)
    if "成长月报" in title:
        lines = [title.replace("成长月报", "").strip(), "成长月报"]
    else:
        lines = wrap_text(title, title_font, 920, 2)
    y = 105
    for line in lines:
        bbox = draw.textbbox((190, y), line, font=title_font)
        draw.text((190, y), line, font=title_font, fill=COLORS["blue"])
        infos.append(TextBoxInfo(line, bbox, bbox))
        y += 116
    draw_wave_line(draw, 195, y + 6, 470, fill="#E9B86D")
    draw_star(draw, 1090, 145, 24)
    draw_heart(draw, 1135, 348, 17)

    draw_dots(draw, 1215, 238, 12, fill="#E7C869")
    draw_sparkle(draw, 1510, 222, 13, fill="#7DA1B6")
    draw.line((1580, 245, 1745, 245), fill=(*_rgb("#7DA1B6"), 120), width=3)
    for xx in range(1590, 1745, 34):
        draw.line((xx, 245, xx + 16, 245), fill=(*_rgb("#7DA1B6"), 170), width=3)

    month_font = find_font(62, bold=True)
    name_font = find_font(52, bold=True)
    draw.ellipse((1880, 120, 2115, 355), fill=COLORS["yellow"], outline="#E7CE73", width=4)
    draw.text((1930, 188), month, font=month_font, fill=COLORS["ink"])
    draw.rounded_rectangle((1825, 365, 2210, 455), radius=20, fill=COLORS["blue_soft"], outline=COLORS["white"], width=4)
    draw_tape(draw, 1910, 335, 200, 48, fill="#F2DFA5")
    draw.text((1930, 382), child_name, font=name_font, fill=COLORS["blue"])
    infos.append(TextBoxInfo(month, (1880, 120, 235, 235), (1930, 188, 2100, 278)))
    infos.append(TextBoxInfo(child_name, (1825, 365, 385, 90), (1930, 382, 2100, 448)))
    return infos


def render_caption_note(text: str, style: str, max_width: int, seed: int) -> tuple[Image.Image, TextBoxInfo]:
    rng = random.Random(seed)
    style = NOTE_STYLES.get(style, style)
    horizontal_padding = 150
    font, lines, warning = fit_text(text, max_width - horizontal_padding, 34, 28, 2)
    line_h = 43
    content_w = _measured_text_width(lines, font)
    paper_w = max(min(max_width, content_w + horizontal_padding), 350)
    paper_h = 108 + line_h * max(1, len(lines))
    layer = Image.new("RGBA", (paper_w + 112, paper_h + 112), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")

    x, y0 = 44, 38
    variant = _caption_variant(style)
    _draw_soft_shadow(draw, x + 10, y0 + 12, paper_w, paper_h, rng)
    far_poly = _draw_paper_shape(
        draw,
        x + variant["far_dx"],
        y0 + variant["far_dy"],
        paper_w,
        paper_h,
        rng,
        variant["far"],
        "torn",
        13,
        outline="#FFFFFF",
    )
    _add_paper_texture(draw, far_poly, rng, 12)
    _draw_paper_shape(draw, x + variant["back_dx"], y0 + variant["back_dy"], paper_w, paper_h, rng, variant["back"], variant["back_shape"], 12, outline=None)
    main_poly = _draw_paper_shape(draw, x, y0, paper_w, paper_h, rng, variant["main"], variant["main_shape"], 11, outline=variant["outline"])
    _add_paper_texture(draw, main_poly, rng, variant["texture"])
    _draw_note_extras(layer, draw, style, x, y0, paper_w, paper_h, rng)

    text_x = x + 72
    y = y0 + 50
    for line in lines:
        draw.text((text_x, y), line, font=font, fill=variant["text"])
        y += line_h
    info = TextBoxInfo(text=text, bbox=(0, 0, layer.width, layer.height), text_bbox=(text_x, y0 + 50, x + paper_w - 62, y), warning=warning)
    return layer, info


def render_summary(canvas: Image.Image, summary: str, seed: int, month: str = "9月") -> TextBoxInfo:
    draw = ImageDraw.Draw(canvas, "RGBA")
    rng = random.Random(seed + 90)
    x, y, w, h = 180, 2875, 2120, 330
    far_poly = _paper_polygon(x - 24, y + 62, w + 58, h - 8, rng, jitter=13, steps=11, shape="torn")
    back_poly = _paper_polygon(x + 28, y + 38, w - 5, h, rng, jitter=12, steps=10, shape="wave")
    main_poly = _paper_polygon(x, y, w, h, rng, jitter=12, steps=11, shape="torn")
    draw.polygon(far_poly, fill=(*_rgb(PALETTE["warm_beige"]), 226))
    draw.line(far_poly + [far_poly[0]], fill=(255, 255, 255, 150), width=4)
    draw.polygon(back_poly, fill=(*_rgb(PALETTE["soft_blue"]), 230))
    draw.line(back_poly + [back_poly[0]], fill=(255, 255, 255, 165), width=4)
    draw.polygon(main_poly, fill=(*_rgb(PALETTE["cream_yellow"]), 236))
    draw.line(main_poly + [main_poly[0]], fill=(255, 255, 255, 185), width=5)
    _add_paper_texture(draw, main_poly, rng, alpha=22)
    _paste_rotated_tape(canvas, x + 175, y - 26, 270, 58, "#DCECF6", -2.0)
    _paste_rotated_tape(canvas, x + w - 500, y - 18, 250, 55, "#E3EDD8", 1.8)
    draw.polygon([(x - 70, y + 88), (x + 58, y + 72), (x + 48, y + 178), (x - 82, y + 194)], fill=(*_rgb(PALETTE["apricot"]), 224))
    draw.line((x - 55, y + 104, x + 38, y + 92), fill=(255, 255, 255, 145), width=3)
    small = find_font(34, bold=True)
    font, lines, warning = fit_text(summary, w - 340, 62, 44, 2)
    draw_star(draw, x + 58, y + 80, 18, fill="#EBC85F")
    draw_star(draw, x + 112, y + 52, 13, fill="#7DA1B6")
    draw_leaf(draw, x + w - 165, y + 94, 23, fill="#91AF7A")
    draw_leaf(draw, x + w - 120, y + 122, 17, fill="#A8BE8E")
    month_label = {"9月": "SEPTEMBER", "10月": "OCTOBER"}.get(month, month)
    draw.text((x + 105, y + 54), month_label, font=small, fill="#7DA1B6")
    draw_dots(draw, x + 430, y + 72, 8, fill="#E7C869")
    for dash_x in range(x + 92, x + w - 115, 42):
        draw.line((dash_x, y + h - 22, dash_x + 20, y + h - 22), fill=(112, 148, 165, 95), width=3)
    yy = y + 130
    for line in lines:
        draw.text((x + 105, yy), line, font=font, fill=PALETTE["text_warm"])
        yy += 68
    draw_wave_line(draw, x + 100, y + h - 50, w - 320, amp=7, fill="#8DB4C9")
    draw_heart(draw, x + w - 235, y + 205, 18, fill="#E8A4A5")
    draw_sparkle(draw, x + w - 82, y + 68, 18, fill="#E7C869")
    return TextBoxInfo(summary, (x, y - 35, w + 70, h + 75), (x + 105, y + 124, x + w - 235, yy), warning)


def paste_text_layer(canvas: Image.Image, layer: Image.Image, x: int, y: int, rotation: float = 0) -> tuple[int, int, int, int]:
    rotated = rotate_layer(layer, rotation)
    canvas.alpha_composite(rotated, (x, y))
    return (x, y, rotated.width, rotated.height)


def _rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def _measured_text_width(lines: list[str], font: ImageFont.ImageFont) -> int:
    img = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(img)
    if not lines:
        return 0
    return max(draw.textbbox((0, 0), line, font=font)[2] for line in lines)


def _caption_variant(style: str) -> dict:
    variants = {
        "note_torn_yellow": {
            "main": PALETTE["cream_yellow"],
            "back": PALETTE["soft_blue"],
            "main_shape": "torn",
            "back_shape": "wave",
            "back_dx": 18,
            "back_dy": 16,
            "far": PALETTE["apricot"],
            "far_dx": -15,
            "far_dy": 23,
            "outline": "#FFFFFF",
            "texture": 18,
            "text": PALETTE["text_warm"],
        },
        "note_blue_lines": {
            "main": PALETTE["soft_blue"],
            "back": PALETTE["warm_beige"],
            "main_shape": "soft_round",
            "back_shape": "trapezoid",
            "back_dx": -12,
            "back_dy": 18,
            "far": PALETTE["gray_blue"],
            "far_dx": 20,
            "far_dy": 25,
            "outline": "#FFFFFF",
            "texture": 16,
            "text": PALETTE["text"],
        },
        "note_green_sprout": {
            "main": PALETTE["sage"],
            "back": PALETTE["cream_yellow"],
            "main_shape": "trapezoid",
            "back_shape": "torn",
            "back_dx": 16,
            "back_dy": -8,
            "far": PALETTE["soft_blue"],
            "far_dx": -15,
            "far_dy": 22,
            "outline": "#F9FAF3",
            "texture": 18,
            "text": PALETTE["text_warm"],
        },
        "note_warm_heart": {
            "main": PALETTE["warm_beige"],
            "back": PALETTE["apricot"],
            "main_shape": "wave",
            "back_shape": "torn",
            "back_dx": 14,
            "back_dy": 18,
            "far": PALETTE["cream_yellow"],
            "far_dx": -16,
            "far_dy": 25,
            "outline": "#FFFFFF",
            "texture": 17,
            "text": PALETTE["text_warm"],
        },
    }
    return variants.get(style, variants["note_torn_yellow"])


def _draw_soft_shadow(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, rng: random.Random) -> None:
    for off, alpha in [(7, 22), (14, 14), (21, 8)]:
        poly = _paper_polygon(x + off, y + off, w, h, rng, jitter=7, steps=5, shape="wave")
        draw.polygon(poly, fill=(130, 120, 103, alpha))


def _draw_paper_shape(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    rng: random.Random,
    fill: str,
    shape: str,
    jitter: int,
    outline: str | None,
) -> list[tuple[int, int]]:
    poly = _paper_polygon(x, y, w, h, rng, jitter=jitter, steps=6, shape=shape)
    draw.polygon(poly, fill=(*_rgb(fill), 236))
    if outline:
        draw.line(poly + [poly[0]], fill=(*_rgb(outline), 190), width=4)
    return poly


def _paper_polygon(
    x: int,
    y: int,
    w: int,
    h: int,
    rng: random.Random,
    jitter: int = 10,
    steps: int = 6,
    shape: str = "torn",
) -> list[tuple[int, int]]:
    if shape == "soft_round":
        return [
            (x + 18, y + rng.randint(-jitter, jitter)),
            (x + w - 24, y + rng.randint(-jitter, jitter)),
            (x + w + rng.randint(-jitter, jitter), y + 22),
            (x + w - 8, y + h - 20),
            (x + w - 28, y + h + rng.randint(-jitter, jitter)),
            (x + 18, y + h + rng.randint(-jitter, jitter)),
            (x + rng.randint(-jitter, jitter), y + h - 18),
            (x + rng.randint(-jitter, jitter), y + 20),
        ]
    if shape == "trapezoid":
        skew_top = rng.randint(-12, 14)
        skew_bottom = rng.randint(-16, 14)
        return [
            (x + 22 + skew_top, y + rng.randint(-jitter, jitter)),
            (x + w - 12 + skew_top, y + rng.randint(-jitter, jitter)),
            (x + w + skew_bottom, y + h + rng.randint(-jitter, jitter)),
            (x - 6 + skew_bottom, y + h + rng.randint(-jitter, jitter)),
        ]
    pts: list[tuple[int, int]] = []
    for i in range(steps + 1):
        amp = rng.randint(-jitter, jitter)
        if shape == "wave":
            amp += int(4 * (-1 if i % 2 else 1))
        pts.append((x + i * w // steps, y + amp))
    for i in range(1, steps + 1):
        pts.append((x + w + rng.randint(-jitter, jitter), y + i * h // steps))
    for i in range(steps - 1, -1, -1):
        dip = rng.randint(-jitter, jitter)
        if shape == "torn" and i in {1, 4}:
            dip += rng.randint(5, 12)
        pts.append((x + i * w // steps, y + h + dip))
    for i in range(steps - 1, 0, -1):
        pts.append((x + rng.randint(-jitter, jitter), y + i * h // steps))
    return pts


def _add_paper_texture(draw: ImageDraw.ImageDraw, poly: list[tuple[int, int]], rng: random.Random, alpha: int = 16) -> None:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    for _ in range(max(18, (x1 - x0) * (y1 - y0) // 9000)):
        x = rng.randint(x0, x1)
        y = rng.randint(y0, y1)
        c = rng.randint(220, 255)
        draw.ellipse((x, y, x + 2, y + 2), fill=(c, c, c, alpha))
    for _ in range(8):
        x = rng.randint(x0 + 20, max(x0 + 21, x1 - 50))
        y = rng.randint(y0 + 16, max(y0 + 17, y1 - 16))
        draw.line((x, y, x + rng.randint(16, 45), y + rng.randint(-2, 2)), fill=(170, 160, 142, max(8, alpha - 5)), width=1)


def _draw_note_extras(layer: Image.Image, draw: ImageDraw.ImageDraw, style: str, x: int, y: int, w: int, h: int, rng: random.Random) -> None:
    if style == "note_torn_yellow":
        _paste_rotated_tape(layer, x + 18, y - 20, 150, 42, "#DCECF6", -2.2)
        draw_star(draw, x + w - 28, y + h - 18, 15, fill="#7EA9C1")
        draw_sparkle(draw, x + w - 64, y + 32, 10, fill="#E7C869")
    elif style == "note_blue_lines":
        draw.line((x + 30, y + 42, x + 92, y + 34), fill="#7DA1B6", width=4)
        draw.line((x + 32, y + 62, x + 86, y + 57), fill="#7DA1B6", width=3)
        draw.line(_paper_polygon(x + 8, y + 8, w - 16, h - 16, rng, jitter=4, steps=5, shape="wave") + [(x + 16, y + 8)], fill=(255, 255, 255, 145), width=2)
        draw_heart(draw, x + w - 36, y + 34, 9, fill="#E8A4A5")
    elif style == "note_green_sprout":
        _paste_rotated_tape(layer, x + w - 172, y - 18, 150, 40, "#F2DFA5", 2.5)
        draw_leaf(draw, x + w - 48, y + h - 30, 14, fill="#8DAE75")
        draw_dots(draw, x + 42, y + h - 32, 3, fill="#E2BD68")
        draw.line((x + 58, y + h - 24, x + 120, y + h - 21), fill=(255, 255, 255, 135), width=3)
    else:
        _paste_rotated_tape(layer, x + w // 2 - 70, y - 18, 145, 40, "#DCECF6", -1.5)
        draw_heart(draw, x + w - 28, y + h // 2, 10, fill="#E8A4A5")
        draw_star(draw, x + 32, y + h - 24, 12, fill="#E7C869")
        draw.line((x + w - 72, y + 38, x + w - 42, y + 22), fill="#7DA1B6", width=3)


def _paste_rotated_tape(canvas: Image.Image, x: int, y: int, w: int, h: int, fill: str, angle: float) -> None:
    tape = Image.new("RGBA", (w + 18, h + 18), (0, 0, 0, 0))
    tape_draw = ImageDraw.Draw(tape, "RGBA")
    draw_tape(tape_draw, 8, 8, w, h, fill=fill)
    rotated = rotate_layer(tape, angle)
    canvas.alpha_composite(rotated, (x, y))

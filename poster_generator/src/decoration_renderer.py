from __future__ import annotations

import math
from typing import Iterable

from PIL import Image, ImageDraw

from utils import COLORS


def draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill: str = COLORS["yellow_deep"]) -> None:
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(angle) * rr, cy + math.sin(angle) * rr))
    draw.polygon(pts, fill=fill)


def draw_sparkle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill: str = COLORS["blue"]) -> None:
    draw.line((cx, cy - r, cx, cy + r), fill=fill, width=max(2, r // 5))
    draw.line((cx - r, cy, cx + r, cy), fill=fill, width=max(2, r // 5))
    draw.line((cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2), fill=fill, width=1)
    draw.line((cx - r // 2, cy + r // 2, cx + r // 2, cy - r // 2), fill=fill, width=1)


def draw_heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, fill: str = COLORS["heart"]) -> None:
    s = size
    pts = [
        (cx, cy + int(0.55 * s)),
        (cx - int(0.95 * s), cy - int(0.1 * s)),
        (cx - int(0.42 * s), cy - int(0.75 * s)),
        (cx, cy - int(0.32 * s)),
        (cx + int(0.42 * s), cy - int(0.75 * s)),
        (cx + int(0.95 * s), cy - int(0.1 * s)),
    ]
    draw.polygon(pts, fill=fill)
    draw.ellipse((cx - s, cy - s, cx, cy), fill=fill)
    draw.ellipse((cx, cy - s, cx + s, cy), fill=fill)


def draw_leaf(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, fill: str = "#7DA97B") -> None:
    draw.ellipse((cx - size, cy - size // 2, cx + size, cy + size // 2), fill=fill)
    draw.line((cx - size, cy, cx + size, cy), fill="#5F895D", width=max(1, size // 8))


def draw_flower(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
        draw.ellipse((cx + dx * size - size, cy + dy * size - size, cx + dx * size + size, cy + dy * size + size), fill="#F2B8C0")
    draw.ellipse((cx - size // 2, cy - size // 2, cx + size // 2, cy + size // 2), fill=COLORS["yellow_deep"])


def draw_doodle_line(draw: ImageDraw.ImageDraw, points: Iterable[tuple[int, int]], fill: str = COLORS["blue"]) -> None:
    pts = list(points)
    if len(pts) > 1:
        draw.line(pts, fill=fill, width=4, joint="curve")


def draw_wave_line(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, amp: int = 8, fill: str = COLORS["blue"]) -> None:
    pts = [(x + i, y + int(math.sin(i / 18) * amp)) for i in range(0, w, 8)]
    draw.line(pts, fill=fill, width=3)


def draw_dashed_line(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, fill: str = COLORS["ink"]) -> None:
    steps = 18
    for i in range(0, steps, 2):
        xa = x1 + (x2 - x1) * i // steps
        ya = y1 + (y2 - y1) * i // steps
        xb = x1 + (x2 - x1) * (i + 1) // steps
        yb = y1 + (y2 - y1) * (i + 1) // steps
        draw.line((xa, ya, xb, yb), fill=fill, width=3)


def draw_tape(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, fill: str = "#CFE4F0") -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=(*_rgb(fill), 176))
    draw.line((x + 10, y + h // 2, x + w - 10, y + h // 2), fill=(255, 255, 255, 85), width=2)


def draw_pin(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 13) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#E7A5A5", outline="#C77B7B", width=3)
    draw.line((cx, cy + r, cx + 12, cy + 42), fill="#9C9C9C", width=3)


def draw_paper_clip(draw: ImageDraw.ImageDraw, x: int, y: int, h: int = 80) -> None:
    draw.rounded_rectangle((x, y, x + 30, y + h), radius=15, outline="#8FAEC2", width=5)
    draw.rounded_rectangle((x + 8, y + 14, x + 22, y + h - 10), radius=8, outline="#8FAEC2", width=4)


def draw_dots(draw: ImageDraw.ImageDraw, x: int, y: int, count: int, fill: str = COLORS["yellow_deep"]) -> None:
    for i in range(count):
        draw.ellipse((x + i * 22, y, x + i * 22 + 8, y + 8), fill=fill)


def decorate_canvas(canvas: Image.Image) -> None:
    """Add a few deliberate decoration clusters instead of scattered motifs."""
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Title connection cluster.
    draw_star(draw, 1745, 278, 18)
    draw_sparkle(draw, 1790, 320, 13)
    draw_wave_line(draw, 1615, 340, 150, amp=5, fill="#8DB4C9")

    # Upper photo-group cluster.
    draw_leaf(draw, 2260, 720, 22)
    draw_dots(draw, 2140, 770, 4, fill="#E2BD68")

    # Middle transition cluster.
    draw_leaf(draw, 185, 1880, 18)
    draw_sparkle(draw, 225, 1842, 11)
    draw_dots(draw, 145, 1920, 3, fill="#E2BD68")

    # Bottom notebook cluster.
    draw_flower(draw, 145, 2815, 14)
    draw_dashed_line(draw, 180, 2820, 315, 2820, fill="#8DB4C9")
    draw_heart(draw, 330, 2818, 10)


def _rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

from utils import CANVAS_SIZE, COLORS, jittered_polygon


def render_background(seed: int) -> Image.Image:
    rng = random.Random(seed)
    canvas = Image.new("RGBA", CANVAS_SIZE, COLORS["paper_alt"])
    draw = ImageDraw.Draw(canvas, "RGBA")

    _draw_base_wash(draw, rng)
    _draw_group_supports(draw, rng)
    _draw_large_scrap_papers(draw, rng)
    _draw_edge_scraps(draw, rng)
    _draw_background_doodles(draw, rng)
    _draw_paper_grain(draw, rng)

    return canvas


def _draw_base_wash(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    washes = [
        (70, 150, 1180, 470, "#DCECF6", 70),
        (1260, 200, 1060, 500, "#F7E7A9", 72),
        (45, 480, 2325, 735, "#F3E7D3", 82),
        (45, 1090, 2335, 920, "#DCECF6", 78),
        (45, 1930, 2335, 900, "#E3EDD8", 82),
        (95, 2865, 2240, 430, "#F7E7A9", 62),
    ]
    for x, y, w, h, color, alpha in washes:
        poly = _paper_shape(x, y, w, h, rng, "natural")
        draw.polygon(poly, fill=(*_hex_to_rgb(color), alpha))


def _draw_group_supports(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    """Build three connected paper fields behind the photo rows."""
    groups = [
        (55, 470, 2360, 790, "#DCECF6", "#F7E7A9"),
        (40, 1120, 2390, 900, "#F3E7D3", "#DCECF6"),
        (55, 1950, 2360, 890, "#E3EDD8", "#F6E2D1"),
    ]
    shapes = ["natural", "wave", "regular"]
    for index, (x, y, w, h, main, back) in enumerate(groups):
        back_poly = _paper_shape(x + (20 if index % 2 == 0 else -8), y + 24, w, h, rng, "regular")
        main_poly = _paper_shape(x, y, w, h, rng, shapes[index])
        draw.polygon(back_poly, fill=(*_hex_to_rgb(back), 132))
        draw.line(back_poly + [back_poly[0]], fill=(*_hex_to_rgb(back), 150), width=3)
        draw.polygon(main_poly, fill=(*_hex_to_rgb(main), 164))
        draw.line(main_poly + [main_poly[0]], fill=(*_hex_to_rgb(main), 180), width=3)

        # A long inset strip binds the three photos into one collage group.
        strip_y = y + h - 125
        strip = _wave_strip(x + 85, strip_y, w - 170, 78, rng, amp=10)
        strip_color = "#F7E7A9" if index != 1 else "#E3EDD8"
        draw.polygon(strip, fill=(*_hex_to_rgb(strip_color), 120))
        for dot_x in range(x + 150, x + w - 120, 52):
            draw.ellipse((dot_x, y + 48, dot_x + 7, y + 55), fill=(116, 145, 158, 54))


def _draw_large_scrap_papers(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    scraps = [
        (110, 95, 970, 285, "#F7E7A9", 168, "natural"),
        (75, 370, 1080, 260, "#DCECF6", 118, "wave"),
        (1270, 145, 960, 330, "#F7E7A9", 142, "regular"),
        (1180, 475, 1020, 230, "#E3EDD8", 72, "wave"),
        (55, 620, 2260, 570, "#F6E2D1", 80, "regular"),
        (120, 1095, 2200, 800, "#DCECF6", 92, "natural"),
        (235, 1290, 1970, 560, "#F7E7A9", 60, "wave"),
        (55, 1940, 2260, 735, "#E3EDD8", 90, "natural"),
        (250, 2170, 1960, 480, "#F3E7D3", 62, "regular"),
        (90, 2865, 2260, 420, "#F7E7A9", 116, "jagged"),
        (125, 2975, 2160, 305, "#DCECF6", 78, "wave"),
    ]
    for x, y, w, h, color, alpha, shape in scraps:
        _draw_scrap(draw, x, y, w, h, rng, color, alpha, shape=shape)

    ribbons = [
        (260, 505, 1880, 92, "#DCECF6", 60),
        (135, 1030, 2190, 92, "#F7E7A9", 52),
        (230, 1905, 2040, 92, "#F3E7D3", 54),
        (120, 2760, 2220, 96, "#DCECF6", 58),
        (145, 3040, 2180, 110, "#F7E7A9", 58),
    ]
    for x, y, w, h, color, alpha in ribbons:
        pts = _wave_strip(x, y, w, h, rng, amp=14)
        draw.polygon(pts, fill=(*_hex_to_rgb(color), alpha))


def _draw_edge_scraps(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    scraps = [
        (-35, 830, 170, 330, "#F7E7A9", 48),
        (2355, 845, 170, 330, "#DCECF6", 42),
        (-45, 1780, 180, 310, "#E3EDD8", 42),
        (2350, 1790, 180, 310, "#F6E2D1", 38),
        (260, -30, 500, 92, "#DCECF6", 42),
        (1480, -35, 610, 100, "#F7E7A9", 42),
    ]
    for x, y, w, h, color, alpha in scraps:
        _draw_scrap(draw, x, y, w, h, rng, color, alpha, shape="natural")


def _draw_background_doodles(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    for x, y, w, amp, color in [
        (260, 485, 430, 8, "#5589AA"),
        (1450, 485, 460, 7, "#E5BD61"),
        (310, 1225, 420, 7, "#7FA6BB"),
        (1690, 1225, 430, 7, "#9FB68F"),
        (420, 2000, 460, 7, "#E5BD61"),
        (1510, 2005, 520, 7, "#7FA6BB"),
    ]:
        pts = [(x + i, y + int(math.sin(i / 19) * amp)) for i in range(0, w, 8)]
        draw.line(pts, fill=(*_hex_to_rgb(color), 112), width=3)

    for x, y, w, h in [(1550, 560, 360, 60), (345, 1045, 280, 50), (1700, 1965, 410, 50), (1760, 2940, 410, 50)]:
        _draw_dot_path(draw, x, y, w, h, rng)

    for _ in range(34):
        x = rng.randrange(120, CANVAS_SIZE[0] - 160)
        y = rng.randrange(180, CANVAS_SIZE[1] - 210)
        if 760 < y < 2800 and 180 < x < 2300:
            alpha = 28
        else:
            alpha = 52
        length = rng.randrange(34, 92)
        draw.line((x, y, x + length, y + rng.randrange(-5, 6)), fill=(144, 132, 112, alpha), width=2)


def _draw_paper_grain(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    for _ in range(5200):
        x = rng.randrange(CANVAS_SIZE[0])
        y = rng.randrange(CANVAS_SIZE[1])
        alpha = rng.randrange(6, 16)
        c = rng.randrange(178, 232)
        draw.point((x, y), fill=(c, c, c, alpha))

    for _ in range(145):
        x = rng.randrange(0, CANVAS_SIZE[0])
        y = rng.randrange(0, CANVAS_SIZE[1])
        length = rng.randrange(28, 110)
        draw.line((x, y, x + length, y + rng.randrange(-3, 4)), fill=(190, 182, 165, 14), width=1)


def _draw_corner_motifs(draw: ImageDraw.ImageDraw) -> None:
    _draw_small_star(draw, 305, 210, 22, "#F2D574", 150)
    _draw_small_star(draw, 2150, 310, 24, "#F2D574", 150)
    _draw_small_star(draw, 2120, 3035, 18, "#F2D574", 145)
    _draw_small_star(draw, 280, 3180, 17, "#F2D574", 145)
    _draw_heart(draw, 1125, 345, 18, "#E8A4A5", 132)
    _draw_heart(draw, 1680, 3188, 15, "#E8A4A5", 122)
    _draw_leaf(draw, 2210, 765, 28, "#7DA97B", 116)
    _draw_leaf(draw, 2145, 3220, 22, "#8AAE74", 112)
    _draw_flower(draw, 190, 2870, 18, 128)


def _draw_scrap(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    rng: random.Random,
    color: str,
    alpha: int,
    shape: str,
) -> None:
    poly = _paper_shape(x, y, w, h, rng, shape)
    draw.polygon([(px + 5, py + 6) for px, py in poly], fill=(132, 124, 108, 3))
    draw.polygon(poly, fill=(*_hex_to_rgb(color), alpha))
    draw.line(poly + [poly[0]], fill=(*_hex_to_rgb(color), min(150, alpha + 18)), width=2)
    for _ in range(max(12, w * h // 36000)):
        px = rng.randint(max(0, x), min(CANVAS_SIZE[0] - 1, x + w))
        py = rng.randint(max(0, y), min(CANVAS_SIZE[1] - 1, y + h))
        draw.line((px, py, px + rng.randint(12, 48), py + rng.randint(-2, 2)), fill=(156, 145, 124, 15), width=1)


def _paper_shape(x: int, y: int, w: int, h: int, rng: random.Random, shape: str) -> list[tuple[int, int]]:
    if shape == "wave":
        return _wave_strip(x, y, w, h, rng, amp=12)
    if shape == "regular":
        top_shift = rng.randint(-8, 8)
        bottom_shift = rng.randint(-10, 10)
        return [
            (x + 8 + top_shift, y + rng.randint(-5, 5)),
            (x + w - 10 + top_shift, y + rng.randint(-5, 5)),
            (x + w + bottom_shift, y + h + rng.randint(-6, 6)),
            (x - 4 + bottom_shift, y + h + rng.randint(-6, 6)),
        ]
    if shape == "jagged":
        return jittered_polygon(x, y, w, h, rng, jitter=28, steps=8)
    return jittered_polygon(x, y, w, h, rng, jitter=9, steps=12)


def _wave_strip(x: int, y: int, w: int, h: int, rng: random.Random, amp: int) -> list[tuple[int, int]]:
    top = []
    bottom = []
    steps = 10
    for i in range(steps + 1):
        px = x + i * w // steps
        top.append((px, y + int(math.sin(i * 0.9) * amp) + rng.randint(-6, 6)))
        bottom.append((px, y + h + int(math.cos(i * 0.85) * amp) + rng.randint(-6, 6)))
    return top + list(reversed(bottom))


def _draw_dot_path(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, rng: random.Random) -> None:
    count = 18
    for i in range(count):
        px = x + i * w // count
        py = y + int(math.sin(i / 2.2) * h / 2) + rng.randint(-4, 4)
        draw.ellipse((px, py, px + 8, py + 8), fill=(229, 194, 93, 88))


def _draw_small_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: str, alpha: int) -> None:
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(angle) * rr, cy + math.sin(angle) * rr))
    draw.polygon(pts, fill=(*_hex_to_rgb(color), alpha))


def _draw_heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str, alpha: int) -> None:
    s = size
    fill = (*_hex_to_rgb(color), alpha)
    draw.ellipse((cx - s, cy - s, cx, cy), fill=fill)
    draw.ellipse((cx, cy - s, cx + s, cy), fill=fill)
    draw.polygon([(cx - s, cy - 2), (cx + s, cy - 2), (cx, cy + int(s * 1.05))], fill=fill)


def _draw_leaf(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str, alpha: int) -> None:
    fill = (*_hex_to_rgb(color), alpha)
    draw.ellipse((cx - size, cy - size // 2, cx + size, cy + size // 2), fill=fill)
    draw.line((cx - size, cy, cx + size, cy), fill=(*_hex_to_rgb("#5F895D"), min(180, alpha + 22)), width=3)


def _draw_flower(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, alpha: int) -> None:
    petal = (*_hex_to_rgb("#F2B8C0"), alpha)
    for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
        draw.ellipse((cx + dx * size - size, cy + dy * size - size, cx + dx * size + size, cy + dy * size + size), fill=petal)
    draw.ellipse((cx - size // 2, cy - size // 2, cx + size // 2, cy + size // 2), fill=(*_hex_to_rgb("#F2D574"), alpha))


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

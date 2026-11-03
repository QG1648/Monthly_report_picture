from __future__ import annotations

import hashlib
import math
import os
import random
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont


CANVAS_SIZE = (2480, 3508)
DPI = (300, 300)
SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

COLORS = {
    "paper": "#FAF8F2",
    "paper_alt": "#F8F4EA",
    "blue": "#5589AA",
    "blue_soft": "#DDEEF7",
    "yellow": "#F8E8AE",
    "yellow_deep": "#F2D574",
    "green_soft": "#E6F0DD",
    "beige": "#F4EBDD",
    "ink": "#4C5962",
    "white": "#FFFFFF",
    "shadow": "#B8B0A3",
    "heart": "#E8A4A5",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_project_path(path: str | Path, base: Path | None = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (base or project_root()) / p


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXTS],
        key=lambda p: p.name.lower(),
    )


def fit_contain(src_size: tuple[int, int], box_size: tuple[int, int]) -> tuple[int, int, float]:
    sw, sh = src_size
    bw, bh = box_size
    scale = min(bw / sw, bh / sh)
    return max(1, int(sw * scale)), max(1, int(sh * scale)), scale


def paste_center(canvas: Image.Image, child: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int]:
    x, y, w, h = box
    px = x + (w - child.width) // 2
    py = y + (h - child.height) // 2
    canvas.alpha_composite(child, (px, py))
    return px, py


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def jittered_polygon(
    x: int,
    y: int,
    w: int,
    h: int,
    rng: random.Random,
    jitter: int = 16,
    steps: int = 3,
) -> list[tuple[int, int]]:
    pts: list[tuple[int, int]] = []
    for i in range(steps + 1):
        pts.append((x + i * w // steps, y + rng.randint(-jitter, jitter)))
    for i in range(1, steps + 1):
        pts.append((x + w + rng.randint(-jitter, jitter), y + i * h // steps))
    for i in range(steps - 1, -1, -1):
        pts.append((x + i * w // steps, y + h + rng.randint(-jitter, jitter)))
    for i in range(steps - 1, 0, -1):
        pts.append((x + rng.randint(-jitter, jitter), y + i * h // steps))
    return pts


def rotate_layer(layer: Image.Image, angle: float) -> Image.Image:
    if abs(angle) < 0.01:
        return layer
    return layer.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0))


def rotated_bbox(x: int, y: int, w: int, h: int, angle: float) -> tuple[int, int, int, int]:
    rad = math.radians(angle)
    rw = abs(w * math.cos(rad)) + abs(h * math.sin(rad))
    rh = abs(w * math.sin(rad)) + abs(h * math.cos(rad))
    cx = x + w / 2
    cy = y + h / 2
    return int(cx - rw / 2), int(cy - rh / 2), int(rw), int(rh)


def text_bbox(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont) -> tuple[int, int, int, int]:
    return draw.textbbox(xy, text, font=font)


def load_json(path: Path) -> dict:
    import json

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    import json

    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def flatten(items: Iterable[Sequence]) -> list:
    out = []
    for item in items:
        out.extend(item)
    return out

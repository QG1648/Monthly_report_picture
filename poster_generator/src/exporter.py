from __future__ import annotations

from pathlib import Path

from PIL import Image

from utils import COLORS, DPI, ensure_dir, save_json


def export_png(image: Image.Image, output_path: Path) -> None:
    """Save an opaque PNG by compositing all layers onto the paper base."""
    ensure_dir(output_path.parent)
    rgba = image.convert("RGBA")
    paper = Image.new("RGBA", rgba.size, COLORS["paper_alt"])
    paper.alpha_composite(rgba)
    paper.convert("RGB").save(output_path, "PNG", dpi=DPI)


def export_report(report: dict, output_path: Path) -> None:
    save_json(output_path, report)

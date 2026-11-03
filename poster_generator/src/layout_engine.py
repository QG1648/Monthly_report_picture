from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config_loader import PosterConfig
from image_loader import LoadedPhoto
from utils import CANVAS_SIZE, load_json, project_root


@dataclass
class PhotoSlot:
    index: int
    x: int
    y: int
    width: int
    height: int
    rotation: float
    frame_type: str
    caption_style: str
    caption_dx: int
    caption_dy: int
    caption_x: int | None = None
    caption_y: int | None = None
    caption_width: int | None = None


def load_template(template_name: str) -> dict:
    path = project_root() / "templates" / "growth_monthly_blue.json"
    data = load_json(path)
    templates = data.get("templates", {})
    if template_name not in templates:
        raise ValueError(f"未知模板 {template_name}，可选: {', '.join(templates)}")
    return templates[template_name]


def compute_layout(config: PosterConfig, photos: list[LoadedPhoto]) -> list[PhotoSlot]:
    """Return deterministic slot assignments, with larger slots given to important photos."""
    template = load_template(config.template)
    raw_slots = template["photo_slots"]
    if len(raw_slots) != len(photos):
        raise ValueError(
            f"模板 {config.template} 包含 {len(raw_slots)} 个照片槽位，"
            f"但配置提供了 {len(photos)} 张照片"
        )
    if template.get("assignment") == "ordered":
        ordered_photos = photos
        ordered_slots = raw_slots
    else:
        ordered_photos = sorted(
            photos,
            key=lambda p: (-p.config.importance, p.index),
        )
        ordered_slots = sorted(
            raw_slots,
            key=lambda s: (-(s["width"] * s["height"]), s["y"], s["x"]),
        )
    assigned: dict[int, dict] = {}
    for photo, slot in zip(ordered_photos, ordered_slots):
        assigned[photo.index] = slot

    return [
        PhotoSlot(
            index=p.index,
            x=int(assigned[p.index]["x"]),
            y=int(assigned[p.index]["y"]),
            width=int(assigned[p.index]["width"]),
            height=int(assigned[p.index]["height"]),
            rotation=float(assigned[p.index].get("rotation", 0)),
            frame_type=str(assigned[p.index].get("frame_type", "polaroid")),
            caption_style=str(assigned[p.index].get("caption_style", "note_yellow")),
            caption_dx=int(assigned[p.index].get("caption_dx", 0)),
            caption_dy=int(assigned[p.index].get("caption_dy", 0)),
            caption_x=p.config.caption_x if p.config.caption_x is not None else assigned[p.index].get("caption_x"),
            caption_y=p.config.caption_y if p.config.caption_y is not None else assigned[p.index].get("caption_y"),
            caption_width=(
                p.config.caption_width
                if p.config.caption_width is not None
                else assigned[p.index].get("caption_width")
            ),
        )
        for p in photos
    ]


def safe_area() -> tuple[int, int, int, int]:
    return (120, 120, CANVAS_SIZE[0] - 240, CANVAS_SIZE[1] - 240)

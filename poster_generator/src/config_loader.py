from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from utils import CANVAS_SIZE, load_json, project_root, resolve_project_path


@dataclass(frozen=True)
class PhotoConfig:
    file: str
    caption: str
    importance: int = 1
    caption_x: int | None = None
    caption_y: int | None = None
    caption_width: int | None = None


@dataclass(frozen=True)
class PosterConfig:
    child_name: str
    month: str
    title: str
    summary: str
    output_file: str
    template: str
    seed: int
    photos_dir: Path
    reference_dir: Path
    photos: list[PhotoConfig]
    canvas_size: tuple[int, int] = CANVAS_SIZE


def load_config(config_path: str | Path) -> PosterConfig:
    root = project_root()
    path = resolve_project_path(config_path, root)
    data: dict[str, Any] = load_json(path)

    required = ["child_name", "month", "title", "summary", "photos"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise ValueError(f"配置缺少必填字段: {', '.join(missing)}")

    photos = [
        PhotoConfig(
            file=str(item.get("file", "")).strip(),
            caption=str(item.get("caption", "")).strip(),
            importance=int(item.get("importance", 1)),
            caption_x=int(item["caption_x"]) if item.get("caption_x") is not None else None,
            caption_y=int(item["caption_y"]) if item.get("caption_y") is not None else None,
            caption_width=int(item["caption_width"]) if item.get("caption_width") is not None else None,
        )
        for item in data["photos"]
    ]

    if any(not p.file for p in photos):
        raise ValueError("photos 中存在空 file 字段")

    return PosterConfig(
        child_name=str(data["child_name"]).strip(),
        month=str(data["month"]).strip(),
        title=str(data["title"]).strip(),
        summary=str(data["summary"]).strip(),
        output_file=str(data.get("output_file", "output/xiaoliu_2026_09_growth_monthly.png")),
        template=str(data.get("template", "template_01")),
        seed=int(data.get("seed", 202609)),
        photos_dir=resolve_project_path(data.get("photos_dir", "input/photos"), root),
        reference_dir=resolve_project_path(data.get("reference_dir", "input/reference"), root),
        photos=photos,
    )

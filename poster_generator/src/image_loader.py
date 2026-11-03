from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from config_loader import PhotoConfig
from utils import SUPPORTED_IMAGE_EXTS, scan_images, sha256_file


@dataclass
class LoadedPhoto:
    index: int
    path: Path
    config: PhotoConfig
    image: Image.Image
    original_size: tuple[int, int]
    displayed_size: tuple[int, int] | None = None
    scale: float | None = None
    rotation: float = 0
    cropped: bool = False
    sha256: str = ""
    format: str = ""


def inspect_image(path: Path) -> tuple[tuple[int, int], str]:
    with Image.open(path) as img:
        return img.size, img.format or path.suffix.lower().lstrip(".")


def load_photos(photos_dir: Path, photo_configs: list[PhotoConfig]) -> list[LoadedPhoto]:
    scanned = scan_images(photos_dir)
    expected_count = len(photo_configs)
    if expected_count not in {8, 9, 10, 11}:
        raise ValueError(f"配置 photos 目前仅支持 8 至 11 项，当前为 {expected_count} 项")
    if len(scanned) != expected_count:
        raise ValueError(
            f"照片目录必须正好包含 {expected_count} 张支持格式图片，"
            f"当前为 {len(scanned)} 张: {photos_dir}"
        )

    scanned_names = {p.name for p in scanned}
    missing = [p.file for p in photo_configs if p.file not in scanned_names]
    if missing:
        raise ValueError(f"配置中照片文件不存在于照片目录: {', '.join(missing)}")

    loaded: list[LoadedPhoto] = []
    for idx, cfg in enumerate(photo_configs, start=1):
        path = photos_dir / cfg.file
        if path.suffix.lower() not in SUPPORTED_IMAGE_EXTS:
            raise ValueError(f"不支持的图片格式: {path.name}")
        with Image.open(path) as img:
            fmt = img.format or path.suffix.lower().lstrip(".")
            fixed = ImageOps.exif_transpose(img).convert("RGBA")
            loaded.append(
                LoadedPhoto(
                    index=idx,
                    path=path,
                    config=cfg,
                    image=fixed,
                    original_size=img.size,
                    sha256=sha256_file(path),
                    format=fmt,
                )
            )
    return loaded

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from config_loader import PosterConfig
from image_loader import LoadedPhoto
from layout_engine import PhotoSlot
from utils import CANVAS_SIZE


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_failed(self) -> None:
        if self.errors:
            raise ValueError("Validation failed:\n" + "\n".join(f"- {e}" for e in self.errors))


def validate_inputs(config: PosterConfig, photos: list[LoadedPhoto]) -> ValidationResult:
    result = ValidationResult()
    expected_count = len(config.photos)
    if len(photos) != expected_count:
        result.errors.append(f"Photos: expected {expected_count}, got {len(photos)}")
    for key, value in {
        "title": config.title,
        "child_name": config.child_name,
        "month": config.month,
        "summary": config.summary,
    }.items():
        if not value.strip():
            result.errors.append(f"Missing text: {key}")

    names = [p.path.name for p in photos]
    if len(set(names)) != len(names):
        result.warnings.append("存在重复照片文件名")

    hashes: dict[str, list[str]] = {}
    for p in photos:
        hashes.setdefault(p.sha256, []).append(p.path.name)
    for files in hashes.values():
        if len(files) > 1:
            result.warnings.append(f"发现重复输入照片 SHA256: {', '.join(files)}")

    if len(set(names)) != expected_count:
        result.errors.append("每张照片必须只使用一次")
    return result


def validate_layout(slots: list[PhotoSlot], element_boxes: list[tuple[str, tuple[int, int, int, int]]]) -> ValidationResult:
    result = ValidationResult()
    used = [slot.index for slot in slots]
    if len(used) != len(set(used)):
        result.errors.append("布局中的照片槽位必须唯一")
    cw, ch = CANVAS_SIZE
    for name, (x, y, w, h) in element_boxes:
        if x < 0 or y < 0 or x + w > cw or y + h > ch:
            result.warnings.append(f"元素越界: {name} bbox={(x, y, w, h)}")
    return result


def format_validation_report(input_result: ValidationResult, layout_result: ValidationResult, photos: list[LoadedPhoto]) -> str:
    duplicate_warnings = [w for w in input_result.warnings if "重复" in w]
    out_of_bounds = [w for w in layout_result.warnings if "越界" in w]
    missing_text = [e for e in input_result.errors if "Missing text" in e]
    lines = [
        "Validation passed:" if input_result.ok and layout_result.ok else "Validation completed with issues:",
        f"Photos: {len(photos)}/{len(photos)}",
        f"Duplicate photos: {len(duplicate_warnings)}",
        f"Out of bounds: {len(out_of_bounds)}",
        f"Missing text: {len(missing_text)}",
    ]
    if input_result.warnings or layout_result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {w}" for w in input_result.warnings + layout_result.warnings)
    return "\n".join(lines)

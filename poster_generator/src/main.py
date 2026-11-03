from __future__ import annotations

import argparse
from pathlib import Path

from PIL import ImageDraw

from background_renderer import render_background
from config_loader import load_config
from decoration_renderer import decorate_canvas
from exporter import export_png, export_report
from image_loader import load_photos
from layout_engine import compute_layout, safe_area
from photo_renderer import render_photo_card
from text_renderer import paste_text_layer, render_caption_note, render_summary, render_title
from utils import CANVAS_SIZE, project_root, resolve_project_path
from validation import format_validation_report, validate_inputs, validate_layout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="儿童成长月报自动排版生成工具")
    parser.add_argument("--config", default="example_config.json", help="JSON配置文件路径")
    parser.add_argument("--debug", action="store_true", help="输出debug_layout.png和详细布局信息")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    config = load_config(args.config)
    photos = load_photos(config.photos_dir, config.photos)
    input_result = validate_inputs(config, photos)
    input_result.raise_if_failed()

    canvas = render_background(config.seed)
    text_infos = render_title(canvas, config.title, config.child_name, config.month, config.seed)
    slots = compute_layout(config, photos)

    photo_infos = []
    element_boxes: list[tuple[str, tuple[int, int, int, int]]] = []
    # Build the complete photo collage first, then place notes as foreground
    # corner/side stickers. This keeps irregular notes visible and intentional.
    for photo, slot in zip(photos, slots):
        card, info = render_photo_card(photo, slot)
        canvas.alpha_composite(card, (slot.x, slot.y))
        photo_infos.append(info)
        element_boxes.append((f"photo_{photo.index}", info.bbox))

    for photo, slot in zip(photos, slots):
        caption_w = int(slot.caption_width) if slot.caption_width is not None else min(520, max(370, slot.width - 110))
        caption, caption_info = render_caption_note(photo.config.caption, slot.caption_style, caption_w, config.seed + photo.index)
        cap_x = int(slot.caption_x) if slot.caption_x is not None else slot.x + slot.caption_dx
        cap_y = int(slot.caption_y) if slot.caption_y is not None else slot.y + slot.height + slot.caption_dy
        cap_rotation = -slot.rotation * 0.45
        cap_bbox = paste_text_layer(canvas, caption, cap_x, cap_y, cap_rotation)
        caption_info.bbox = cap_bbox
        text_infos.append(caption_info)
        element_boxes.append((f"caption_{photo.index}", cap_bbox))

    summary_info = render_summary(canvas, config.summary, config.seed, config.month)
    text_infos.append(summary_info)
    element_boxes.append(("summary", summary_info.bbox))
    decorate_canvas(canvas)

    for i, info in enumerate(text_infos):
        element_boxes.append((f"text_{i}", info.bbox))

    layout_result = validate_layout(slots, element_boxes)
    report_text = format_validation_report(input_result, layout_result, photos)
    print(report_text)
    if text_warnings := [t.warning for t in text_infos if t.warning]:
        print("Text warnings:")
        for warning in text_warnings:
            print(f"- {warning}")

    output_path = resolve_project_path(config.output_file, root)
    export_png(canvas, output_path)

    report = build_render_report(config, photos, photo_infos, slots, output_path, input_result.warnings + layout_result.warnings)
    export_report(report, root / "output" / "render_report.json")

    if args.debug:
        debug = canvas.copy()
        draw_debug_overlay(debug, slots, element_boxes)
        export_png(debug, root / "output" / "debug_layout.png")
        print("Debug layout: output/debug_layout.png")
        for slot in slots:
            print(
                f"photo_{slot.index}: x={slot.x}, y={slot.y}, w={slot.width}, h={slot.height}, "
                f"rotation={slot.rotation}, caption=({slot.caption_dx},{slot.caption_dy})"
            )
    print(f"Output: {output_path}")
    print(f"Report: {root / 'output' / 'render_report.json'}")
    return 0


def build_render_report(config, photos, photo_infos, slots, output_path: Path, warnings: list[str]) -> dict:
    info_by_index = {info.index: info for info in photo_infos}
    slot_by_index = {slot.index: slot for slot in slots}
    return {
        "output_file": str(output_path),
        "canvas_size": list(CANVAS_SIZE),
        "dpi": [300, 300],
        "photo_count": len(photos),
        "template": config.template,
        "seed": config.seed,
        "warnings": warnings,
        "photos": [
            {
                "index": p.index,
                "file": str(p.path),
                "format": p.format,
                "sha256": p.sha256,
                "original_width": p.original_size[0],
                "original_height": p.original_size[1],
                "displayed_width": info_by_index[p.index].displayed_size[0],
                "displayed_height": info_by_index[p.index].displayed_size[1],
                "slot_width": slot_by_index[p.index].width,
                "slot_height": slot_by_index[p.index].height,
                "scale": round(info_by_index[p.index].scale, 6),
                "rotation": info_by_index[p.index].rotation,
                "cropped": info_by_index[p.index].cropped,
                "caption": p.config.caption,
                "caption_style": slot_by_index[p.index].caption_style,
                "importance": p.config.importance,
            }
            for p in photos
        ],
    }


def draw_debug_overlay(image, slots, element_boxes) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    sx, sy, sw, sh = safe_area()
    draw.rectangle((sx, sy, sx + sw, sy + sh), outline=(80, 160, 210, 170), width=6)
    for slot in slots:
        draw.rectangle((slot.x, slot.y, slot.x + slot.width, slot.y + slot.height), outline=(255, 0, 0, 190), width=5)
        draw.text((slot.x + 8, slot.y + 8), f"P{slot.index}", fill=(255, 0, 0, 255))
    for name, (x, y, w, h) in element_boxes:
        if name.startswith("caption") or name == "summary":
            draw.rectangle((x, y, x + w, y + h), outline=(0, 120, 0, 150), width=3)


if __name__ == "__main__":
    raise SystemExit(main())

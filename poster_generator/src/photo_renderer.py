from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw

from decoration_renderer import draw_star, draw_tape
from image_loader import LoadedPhoto
from layout_engine import PhotoSlot
from utils import COLORS, fit_contain, paste_center, rotate_layer, rounded_mask


@dataclass
class RenderedPhotoInfo:
    index: int
    bbox: tuple[int, int, int, int]
    photo_box: tuple[int, int, int, int]
    displayed_size: tuple[int, int]
    scale: float
    rotation: float
    cropped: bool


def render_photo_card(photo: LoadedPhoto, slot: PhotoSlot) -> tuple[Image.Image, RenderedPhotoInfo]:
    """Render a photo as a protected content layer inside a decorative card."""
    border_by_type = {
        "narrow": 20,
        "blue_backing": 26,
        "yellow_backing": 26,
        "polaroid": 36,
    }
    border = border_by_type.get(slot.frame_type, 24)
    bottom_extra = 68 if slot.frame_type == "polaroid" else 16
    fitted_w, fitted_h, scale = fit_contain(photo.image.size, (slot.width, slot.height))
    layer_w = slot.width + border * 2 + 70
    layer_h = slot.height + border + bottom_extra + 70
    layer = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")

    # The decorative card follows the contained photo instead of filling the
    # entire slot. This keeps portrait photos intact without creating large
    # white gutters inside a landscape slot.
    card_w, card_h = fitted_w + border * 2, fitted_h + border + bottom_extra
    card_x = 35 + (slot.width - fitted_w) // 2
    card_y = 35 + (slot.height - fitted_h) // 2

    if slot.frame_type in {"blue_backing", "yellow_backing"}:
        backing = COLORS["blue_soft"] if slot.frame_type == "blue_backing" else COLORS["yellow"]
        draw.polygon(
            [
                (card_x + 16, card_y + 18),
                (card_x + card_w + 38, card_y + 30),
                (card_x + card_w + 28, card_y + card_h + 40),
                (card_x + 28, card_y + card_h + 30),
            ],
            fill=backing,
        )

    shadow_steps = [(8, 24), (15, 13)] if slot.frame_type == "narrow" else [(10, 30), (18, 16), (25, 8)]
    for off, alpha in shadow_steps:
        draw.rounded_rectangle((card_x + off, card_y + off, card_x + card_w + off, card_y + card_h + off), radius=24, fill=(120, 112, 96, alpha))
    draw.rounded_rectangle((card_x, card_y, card_x + card_w, card_y + card_h), radius=24, fill=COLORS["white"])

    photo_box = (card_x + border, card_y + border, fitted_w, fitted_h)
    box_layer = Image.new("RGBA", (fitted_w, fitted_h), (255, 255, 255, 255))
    resized = photo.image.resize((fitted_w, fitted_h), Image.Resampling.LANCZOS)
    mask = rounded_mask((fitted_w, fitted_h), radius=18)
    resized.putalpha(mask)
    paste_center(box_layer, resized, (0, 0, fitted_w, fitted_h))
    layer.alpha_composite(box_layer, (photo_box[0], photo_box[1]))

    if slot.frame_type == "polaroid":
        draw_tape(draw, card_x + card_w // 2 - 115, card_y - 22, 230, 58, fill="#CFE4F0")
    elif slot.frame_type == "yellow_backing":
        draw_star(draw, card_x + card_w + 12, card_y + card_h + 10, 18)

    rotated = rotate_layer(layer, slot.rotation)
    info = RenderedPhotoInfo(
        index=photo.index,
        bbox=(slot.x, slot.y, rotated.width, rotated.height),
        photo_box=(slot.x + photo_box[0], slot.y + photo_box[1], slot.width, slot.height),
        displayed_size=(fitted_w, fitted_h),
        scale=scale,
        rotation=slot.rotation,
        cropped=False,
    )
    photo.displayed_size = (fitted_w, fitted_h)
    photo.scale = scale
    photo.rotation = slot.rotation
    photo.cropped = False
    return rotated, info

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import sys
from typing import Any

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from livery.transforms import SlotPlacement, composite_slot_image


SLOTS_PATH = PROJECT_ROOT / "config" / "sponsor_slots.json"
TEST_TRANSFORMS_PATH = PROJECT_ROOT / "config" / "test_slot_transforms.json"
TEST_SAFE_AREAS_PATH = PROJECT_ROOT / "config" / "test_slot_safe_areas.json"
SAFE_AREA_OUTPUT_PATH = (
    PROJECT_ROOT / "generated" / "f1_test_livery_engine_safe_area.png"
)

Color = tuple[int, int, int]
SlotStyle = tuple[str, Color]

SLOT_STYLES: dict[str, SlotStyle] = {
    "sidepod_left": ("SL →", (220, 40, 40)),
    "sidepod_right": ("SR →", (40, 120, 220)),
    "engine_cover_left": ("EL →", (40, 180, 60)),
    "engine_cover_right": ("ER →", (255, 140, 0)),
    "nose_top": ("N →", (150, 60, 200)),
    "bargeboard_left": ("BL →", (255, 210, 0)),
    "bargeboard_right": ("BR →", (0, 200, 200)),
    "frontwing_main": ("FW →", (255, 80, 140)),
    "frontwing_endplate_left": ("FL →", (120, 80, 255)),
    "frontwing_endplate_right": ("FR →", (80, 220, 255)),
    "rearwing_main": ("RW →", (255, 255, 255)),
    "rearwing_side_left": ("RL →", (180, 255, 80)),
    "rearwing_side_right": ("RR →", (255, 180, 80)),
}


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)

    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object in: {path}")

    return value


def try_get_font(size: int) -> ImageFont.ImageFont:
    for font_name in ("arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue

    return ImageFont.load_default()


def create_label_image(label: str) -> Image.Image:
    """Render an asymmetric RGBA label tile that makes flips easy to spot."""
    font = try_get_font(24)
    scratch = Image.new("RGBA", (1, 1))
    scratch_draw = ImageDraw.Draw(scratch)
    left, top, right, bottom = scratch_draw.multiline_textbbox(
        (0, 0), label, font=font, spacing=0, align="center"
    )
    padding = 3
    width = math.ceil(right - left) + padding * 2
    height = math.ceil(bottom - top) + padding * 2

    label_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(label_image)
    position = (padding - left, padding - top)

    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        draw.multiline_text(
            (position[0] + dx, position[1] + dy),
            label,
            font=font,
            fill=(0, 0, 0, 255),
            spacing=0,
            align="center",
        )
    draw.multiline_text(
        position,
        label,
        font=font,
        fill=(255, 255, 255, 255),
        spacing=0,
        align="center",
    )

    return label_image


def draw_slot_overlay(
    overlay: Image.Image,
    slot_info: dict[str, Any],
    label: str,
    color: Color,
    ) -> SlotPlacement:
    bounds = slot_info["pixel_bounds"]
    x = bounds["x"]
    y = bounds["y"]
    width = bounds["width"]
    height = bounds["height"]

    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid slot dimensions: {bounds}")

    right = x + width - 1
    bottom = y + height - 1
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(
        (x, y, right, bottom),
        fill=color + (255,),
        outline=(0, 0, 0, 255),
        width=1,
    )

    return composite_slot_image(
        overlay,
        create_label_image(label),
        slot_info,
        preferred_padding=1,
    )


def generate_test_livery(
    base: Image.Image,
    slots: dict[str, Any],
    output_path: Path,
) -> int:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    drawn_slots = 0

    for slot_name, slot_info in slots.items():
        style = SLOT_STYLES.get(slot_name)
        if style is None:
            continue

        label, color = style
        placement = draw_slot_overlay(
            overlay,
            slot_info,
            label,
            color,
        )
        transform = placement.transform
        x, y, width, height = placement.destination_bounds
        content_x, content_y, content_width, content_height = placement.content_bounds
        transformed_width, transformed_height = placement.transformed_size
        fitted_width, fitted_height = placement.fitted_size
        print(
            f"{slot_name}: "
            f"flip_x={transform.flip_x}, "
            f"flip_y={transform.flip_y}, "
            f"rotation={transform.rotate}, "
            f"transformed={transformed_width}x{transformed_height}, "
            f"fitted={fitted_width}x{fitted_height}, "
            f"bounds=(x={x}, y={y}, width={width}, height={height}), "
            f"content_box=(x={content_x}, y={content_y}, "
            f"width={content_width}, height={content_height})"
        )
        drawn_slots += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(base, overlay).save(output_path)
    return drawn_slots


def add_test_transforms(
    slots: dict[str, Any], transforms: dict[str, Any]
) -> dict[str, Any]:
    unknown_slots = sorted(set(transforms) - set(slots))
    if unknown_slots:
        raise KeyError(
            f"Test transforms contain unknown slots: {', '.join(unknown_slots)}"
        )

    transformed_slots = copy.deepcopy(slots)
    for slot_name, transform in transforms.items():
        transformed_slots[slot_name]["transform"] = transform

    return transformed_slots


def add_test_safe_areas(
    slots: dict[str, Any], safe_areas: dict[str, Any]
) -> dict[str, Any]:
    unknown_slots = sorted(set(safe_areas) - set(slots))
    if unknown_slots:
        raise KeyError(
            f"Test safe areas contain unknown slots: {', '.join(unknown_slots)}"
        )

    safe_slots = copy.deepcopy(slots)
    for slot_name, safe_area in safe_areas.items():
        safe_slots[slot_name]["safe_area"] = safe_area

    return safe_slots


def main() -> None:
    slots = load_json_object(SLOTS_PATH)
    test_transforms = load_json_object(TEST_TRANSFORMS_PATH)
    test_safe_areas = load_json_object(TEST_SAFE_AREAS_PATH)
    transformed_slots = add_test_transforms(slots, test_transforms)
    diagnostic_slots = add_test_safe_areas(transformed_slots, test_safe_areas)

    missing_styles = sorted(set(slots) - set(SLOT_STYLES))
    missing_slots = sorted(set(SLOT_STYLES) - set(slots))
    if missing_styles:
        print(f"[WARNING] No test style for: {', '.join(missing_styles)}")
    if missing_slots:
        print(f"[WARNING] Config does not contain: {', '.join(missing_slots)}")

    base = Image.new("RGBA", (256, 256), (96, 96, 96, 255))

    transformed_count = generate_test_livery(
        base,
        diagnostic_slots,
        SAFE_AREA_OUTPUT_PATH,
    )

    print(f"Generated engine safe-area test livery: {SAFE_AREA_OUTPUT_PATH}")
    print(f"Painted slots: {transformed_count}/{len(slots)}")


if __name__ == "__main__":
    main()

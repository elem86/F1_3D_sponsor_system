from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from livery.config_loader import load_json
from livery.transforms import composite_slot_image


SLOTS_PATH = PROJECT_ROOT / "config" / "sponsor_slots.json"
SPONSORS_PATH = PROJECT_ROOT / "config" / "sponsors.json"
MATRIX_OUTPUT_PATH = PROJECT_ROOT / "generated" / "slot_matrix_test.png"
REPORT_OUTPUT_PATH = PROJECT_ROOT / "generated" / "slot_matrix_report.json"

CELL_WIDTH = 92
CELL_HEIGHT = 96
ROW_LABEL_WIDTH = 104
HEADER_HEIGHT = 72

SLOT_ABBREVIATIONS = {
    "engine_cover_left": "ENG L",
    "engine_cover_right": "ENG R",
    "nose_top": "NOSE",
    "bargeboard_left": "BARGE L",
    "bargeboard_right": "BARGE R",
    "frontwing_main": "FW MAIN",
    "frontwing_endplate_left": "FW END L",
    "frontwing_endplate_right": "FW END R",
    "rearwing_main": "RW MAIN",
    "rearwing_side_left": "RW SIDE L",
    "rearwing_side_right": "RW SIDE R",
    "sidepod_right": "SIDE R",
    "sidepod_left": "SIDE L",
}


def load_font(size: int) -> ImageFont.ImageFont:
    for font_name in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def contain(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    scale = min(max_width / image.width, max_height / image.height)
    size = (
        max(1, int(image.width * scale)),
        max(1, int(image.height * scale)),
    )
    return image.resize(size, Image.Resampling.NEAREST)


def normalized_safe_area(slot: dict[str, Any]) -> dict[str, float]:
    return slot.get(
        "safe_area",
        {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
    )


def main() -> None:
    slots = load_json(SLOTS_PATH)
    sponsors = load_json(SPONSORS_PATH)
    slot_items = list(slots.items())
    sponsor_items = list(sponsors.items())

    matrix_width = ROW_LABEL_WIDTH + CELL_WIDTH * len(slot_items)
    matrix_height = HEADER_HEIGHT + CELL_HEIGHT * len(sponsor_items)
    matrix = Image.new("RGBA", (matrix_width, matrix_height), (28, 32, 42, 255))
    draw = ImageDraw.Draw(matrix)
    header_font = load_font(11)
    row_font = load_font(15)
    detail_font = load_font(9)

    for column, (slot_name, _) in enumerate(slot_items):
        x = ROW_LABEL_WIDTH + column * CELL_WIDTH + CELL_WIDTH // 2
        label = SLOT_ABBREVIATIONS.get(slot_name, slot_name.upper())
        draw.multiline_text(
            (x, HEADER_HEIGHT // 2),
            label.replace(" ", "\n"),
            font=header_font,
            anchor="mm",
            align="center",
            spacing=0,
            fill=(235, 240, 250, 255),
        )

    report_entries: list[dict[str, Any]] = []
    for row, (sponsor_id, sponsor) in enumerate(sponsor_items):
        row_y = HEADER_HEIGHT + row * CELL_HEIGHT
        draw.rectangle(
            (0, row_y, matrix_width - 1, row_y + CELL_HEIGHT - 1),
            outline=(65, 72, 90, 255),
        )
        draw.text(
            (ROW_LABEL_WIDTH // 2, row_y + CELL_HEIGHT // 2),
            sponsor["name"].upper(),
            font=row_font,
            anchor="mm",
            fill=(255, 255, 255, 255),
        )

        logo_path = Path(sponsor["logo"])
        if not logo_path.is_absolute():
            logo_path = PROJECT_ROOT / logo_path
        with Image.open(logo_path) as source:
            logo = source.convert("RGBA")
        source_size = logo.size

        for column, (slot_name, slot) in enumerate(slot_items):
            test_canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            placement = composite_slot_image(test_canvas, logo, slot)
            bounds = slot["pixel_bounds"]
            crop = test_canvas.crop(
                (
                    bounds["x"],
                    bounds["y"],
                    bounds["x"] + bounds["width"],
                    bounds["y"] + bounds["height"],
                )
            )
            preview = contain(crop, CELL_WIDTH - 10, CELL_HEIGHT - 25)

            cell_x = ROW_LABEL_WIDTH + column * CELL_WIDTH
            cell_y = row_y
            draw.rectangle(
                (cell_x, cell_y, cell_x + CELL_WIDTH - 1, cell_y + CELL_HEIGHT - 1),
                outline=(65, 72, 90, 255),
            )
            preview_x = cell_x + (CELL_WIDTH - preview.width) // 2
            preview_y = cell_y + 4 + (CELL_HEIGHT - 25 - preview.height) // 2
            matrix.alpha_composite(preview, (preview_x, preview_y))
            draw.text(
                (cell_x + CELL_WIDTH // 2, cell_y + CELL_HEIGHT - 10),
                f"{placement.fitted_size[0]}x{placement.fitted_size[1]} p{placement.padding}",
                font=detail_font,
                anchor="mm",
                fill=(190, 200, 220, 255),
            )

            transform = placement.transform
            safe_area = normalized_safe_area(slot)
            entry = {
                "slot": slot_name,
                "sponsor": sponsor_id,
                "safe_area": safe_area,
                "transform": {
                    "flip_x": transform.flip_x,
                    "flip_y": transform.flip_y,
                    "rotate": transform.rotate,
                },
                "logo_source_size": {
                    "width": source_size[0],
                    "height": source_size[1],
                },
                "transformed_size": {
                    "width": placement.transformed_size[0],
                    "height": placement.transformed_size[1],
                },
                "final_fitted_size": {
                    "width": placement.fitted_size[0],
                    "height": placement.fitted_size[1],
                },
                "padding": placement.padding,
            }
            report_entries.append(entry)
            print(
                f"{slot_name} -> {sponsor_id} -> "
                f"safe_area={safe_area} -> "
                f"transform=(flip_x={transform.flip_x}, "
                f"flip_y={transform.flip_y}, rotate={transform.rotate}) -> "
                f"source={source_size[0]}x{source_size[1]} -> "
                f"transformed={placement.transformed_size[0]}x"
                f"{placement.transformed_size[1]} -> "
                f"fitted={placement.fitted_size[0]}x{placement.fitted_size[1]} -> "
                f"padding={placement.padding}"
            )

    MATRIX_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    matrix.save(MATRIX_OUTPUT_PATH)
    with REPORT_OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump({"placements": report_entries}, file, indent=4)
        file.write("\n")

    print(f"Generated slot matrix: {MATRIX_OUTPUT_PATH}")
    print(f"Generated placement report: {REPORT_OUTPUT_PATH}")
    print(f"Placement combinations tested: {len(report_entries)}")


if __name__ == "__main__":
    main()

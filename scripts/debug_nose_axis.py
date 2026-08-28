from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from livery.generator import LiveryGenerator

MODEL_DIRECTORY = PROJECT_ROOT / "config" / "models" / "f2002"
SLOTS_PATH = MODEL_DIRECTORY / "sponsor_slots.json"
BASE_PATH = PROJECT_ROOT / "assets" / "models" / "f2002" / "white_base.png"
OUTPUT_PATH = PROJECT_ROOT / "generated" / "debug" / "f2002_nose_axis_livery.png"
LABEL_DIR = PROJECT_ROOT / "generated" / "debug" / "nose_axis_sources"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _font(size: int) -> ImageFont.ImageFont:
    font_directory = Path("C:/Windows/Fonts")
    for candidate in (font_directory / "arialbd.ttf",):
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _label_image(label: str, color: tuple[int, int, int], size=(700, 500)) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((10, 10, size[0] - 10, size[1] - 10), radius=40, fill=color + (255,), outline=(0, 0, 0, 255), width=10)
    font = _font(120)
    draw.text((size[0] // 2, size[1] // 2), label, font=font, anchor="mm", fill=(255, 255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0, 255))
    return canvas


def main() -> None:
    slots = _load(SLOTS_PATH)
    LABEL_DIR.mkdir(parents=True, exist_ok=True)

    # x=0 is the local-left edge of the slot's pixel_bounds; x=1 is local-right.
    # Paint distinct labels at the two extremes of nose_left/nose_right so we can
    # see, in 3D, which end is toward the nose tip (front) vs cockpit (rear).
    specs = {
        "nose_left": [("L-X0", (200, 0, 0), 0.0), ("L-X1", (0, 0, 200), 0.75)],
        "nose_right": [("R-X0", (0, 150, 0), 0.0), ("R-X1", (150, 100, 0), 0.75)],
    }

    sponsors: dict[str, Any] = {}
    assignments: dict[str, str] = {}
    slot_overrides: dict[str, Any] = {}

    for slot_name, markers in specs.items():
        for text, color, x in markers:
            label_path = LABEL_DIR / f"{text}.png"
            _label_image(text, color).save(label_path)
            sponsors[text] = {"logo": str(label_path)}
            override_slot = dict(slots[slot_name])
            override_slot.pop("layout", None)
            override_slot["safe_area"] = {"x": x, "y": 0.05, "width": 0.25, "height": 0.9}
            override_slot["padding"] = 2
            override_slot.pop("transform", None)
            override_name = f"{text}__slot"
            slot_overrides[override_name] = override_slot
            assignments[override_name] = text

    generator = LiveryGenerator(BASE_PATH, slot_overrides, working_scale=1, output_mode="RGB")
    generator.generate(assignments, sponsors, OUTPUT_PATH, team_data=None)
    print(f"Axis livery written: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

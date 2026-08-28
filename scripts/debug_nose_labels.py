from __future__ import annotations

import json
import os
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
TEAM_PATH = PROJECT_ROOT / "config" / "teams" / "default_team.json"
BASE_PATH = PROJECT_ROOT / "assets" / "models" / "f2002" / "white_base.png"
OUTPUT_PATH = PROJECT_ROOT / "generated" / "debug" / "f2002_nose_label_livery.png"
LABEL_DIR = PROJECT_ROOT / "generated" / "debug" / "nose_label_sources"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _font(size: int) -> ImageFont.ImageFont:
    font_directory = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for candidate in (font_directory / "arialbd.ttf", Path("DejaVuSans-Bold.ttf")):
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _label_image(label: str, color: tuple[int, int, int], size=(1400, 500)) -> Image.Image:
    """Render a big, asymmetric (non-mirror-safe) text label with an arrow."""
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (10, 10, size[0] - 10, size[1] - 10),
        radius=50,
        fill=color + (255,),
        outline=(10, 10, 10, 255),
        width=14,
    )
    # Asymmetric corner marker (top-left notch) so flips/rotations are obvious.
    draw.polygon(
        [(10, 10), (10 + size[0] // 6, 10), (10, 10 + size[1] // 4)],
        fill=(255, 255, 0, 255),
    )
    font_size = 260
    while font_size > 30:
        font = _font(font_size)
        box = draw.textbbox((0, 0), label, font=font, stroke_width=6)
        if box[2] - box[0] <= size[0] - 140 and box[3] - box[1] <= size[1] - 140:
            break
        font_size -= 8
    draw.text(
        (size[0] // 2, size[1] // 2),
        label,
        font=font,
        anchor="mm",
        fill=(255, 255, 255, 255),
        stroke_width=8,
        stroke_fill=(0, 0, 0, 255),
    )
    return canvas


TEST_ROTATE = int(os.environ.get("NOSE_TOP_ROTATE", "90"))


def main() -> None:
    slots = _load(SLOTS_PATH)
    team = _load(TEAM_PATH)

    LABEL_DIR.mkdir(parents=True, exist_ok=True)

    # Build synthetic "sponsor" assignments that target the exact reserved /
    # sponsor sub-areas used for nose branding, bypassing the team-asset system
    # so we can drop giant, obviously-oriented placeholder text into each area.
    label_specs = {
        "nose_top_sponsor": (
            "TOP", (30, 110, 200), "nose_top",
            slots["nose_top"]["layout"]["sponsor_area"],
            {"flip_x": False, "flip_y": False, "rotate": TEST_ROTATE},
        ),
        "nose_top_number": (
            "1", (200, 30, 30), "nose_top",
            slots["nose_top"]["layout"]["reserved_areas"][1]["area"],
            {"flip_x": False, "flip_y": False, "rotate": TEST_ROTATE},
        ),
        "nose_left_mark": (
            "AERON-L", (220, 0, 0), "nose_left",
            slots["nose_left"]["layout"]["reserved_areas"][0]["area"],
            slots["nose_left"]["layout"]["reserved_areas"][0].get("transform"),
        ),
        "nose_right_mark": (
            "AERON-R", (0, 170, 0), "nose_right",
            slots["nose_right"]["layout"]["reserved_areas"][0]["area"],
            slots["nose_right"]["layout"]["reserved_areas"][0].get("transform"),
        ),
    }

    sponsors: dict[str, Any] = {}
    assignments: dict[str, str] = {}
    slot_overrides: dict[str, Any] = {}

    for key, (text, color, slot_name, area, area_transform) in label_specs.items():
        label_path = LABEL_DIR / f"{key}.png"
        _label_image(text, color).save(label_path)
        sponsors[key] = {"logo": str(label_path)}
        override_slot = dict(slots[slot_name])
        override_slot.pop("layout", None)
        override_slot["safe_area"] = area
        override_slot["padding"] = 4
        if area_transform is not None:
            override_slot["transform"] = area_transform
        else:
            override_slot.pop("transform", None)
        override_name = f"{key}__slot"
        slot_overrides[override_name] = override_slot
        assignments[override_name] = key

    generator = LiveryGenerator(BASE_PATH, slot_overrides, working_scale=1, output_mode="RGB")
    generator.generate(assignments, sponsors, OUTPUT_PATH, team_data=None)
    print(f"Nose label livery written: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

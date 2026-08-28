from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from livery.generator import LiveryGenerator
from livery.slot_masks import (
    largest_mask_rectangle,
    prepare_slot_mask,
    rasterize_slot_mask,
)


MODEL_DIRECTORY = PROJECT_ROOT / "config" / "models" / "f2002"
SLOTS_PATH = MODEL_DIRECTORY / "sponsor_slots.json"
ASSIGNMENTS_PATH = MODEL_DIRECTORY / "demo_assignments.json"
SPONSORS_PATH = PROJECT_ROOT / "config" / "sponsors.json"
TEAM_PATH = PROJECT_ROOT / "config" / "teams" / "default_team.json"
BASE_PATH = PROJECT_ROOT / "assets" / "models" / "f2002" / "white_base.png"
DIAGNOSTIC_OUTPUT = PROJECT_ROOT / "generated" / "f2002_slot_diagnostic.png"
EXAMPLE_OUTPUT = PROJECT_ROOT / "generated" / "f2002_example_livery.png"
MASK_PREVIEW_DIRECTORY = PROJECT_ROOT / "generated" / "debug" / "f2002_masks"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object in {path}")
    return value


def _absolute_asset_paths(data: dict[str, Any], field: str) -> dict[str, Any]:
    """Return a copy with repository-relative image paths made absolute."""
    resolved: dict[str, Any] = {}
    for key, entry in data.items():
        if not isinstance(entry, dict) or not isinstance(entry.get(field), str):
            raise TypeError(f"{key!r} must define a string {field!r}")
        copied = dict(entry)
        path = Path(copied[field])
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        copied[field] = str(path.resolve())
        resolved[key] = copied
    return resolved


def _absolute_team_paths(team: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(team)
    assets = team.get("assets")
    if not isinstance(assets, dict):
        raise TypeError("Team config must define an assets object")
    resolved["assets"] = {
        asset_id: str((PROJECT_ROOT / configured_path).resolve())
        for asset_id, configured_path in assets.items()
    }
    return resolved


def _font(size: int) -> ImageFont.ImageFont:
    font_directory = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for candidate in (font_directory / "arialbd.ttf", Path("DejaVuSans-Bold.ttf")):
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _label_image(label: str, color: tuple[int, int, int]) -> Image.Image:
    """Render a large asymmetric marker that makes mirroring easy to spot."""
    size = (1600, 400)
    canvas = Image.new("RGBA", size)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (12, 12, size[0] - 12, size[1] - 12),
        radius=70,
        fill=color + (238,),
        outline=(12, 20, 34, 255),
        width=18,
    )
    font_size = 230
    while font_size > 40:
        font = _font(font_size)
        box = draw.textbbox((0, 0), label, font=font, stroke_width=5)
        if box[2] - box[0] <= size[0] - 100:
            break
        font_size -= 10
    draw.text(
        (size[0] // 2, size[1] // 2),
        label,
        font=font,
        anchor="mm",
        fill=(255, 255, 255, 255),
        stroke_width=9,
        stroke_fill=(12, 20, 34, 255),
    )
    return canvas


def _write_mask_previews(slots: dict[str, Any]) -> None:
    """Save raw/effective masks and the contained fit rectangle for each slot."""
    MASK_PREVIEW_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for slot_name, slot in slots.items():
        raw_mask = rasterize_slot_mask(slot)
        sponsor_slot = LiveryGenerator._sponsor_slot(slot)
        effective_mask = prepare_slot_mask(sponsor_slot)
        if raw_mask is None or effective_mask is None:
            raise ValueError(f"F2002 slot {slot_name!r} has no production mask")
        preview = Image.new("RGB", raw_mask.size, (16, 20, 28))
        preview.paste((80, 88, 104), mask=raw_mask)
        preview.paste((35, 194, 142), mask=effective_mask)
        x, y, width, height = largest_mask_rectangle(effective_mask)
        draw = ImageDraw.Draw(preview)
        draw.rectangle(
            (x, y, x + width - 1, y + height - 1),
            outline=(255, 82, 82),
            width=max(1, min(raw_mask.size) // 120),
        )
        preview_path = MASK_PREVIEW_DIRECTORY / f"{slot_name}.png"
        preview.save(preview_path, format="PNG")
        print(f"Mask preview: {slot_name} -> {preview_path}")


def main() -> None:
    slots = _load(SLOTS_PATH)
    assignments = _load(ASSIGNMENTS_PATH)
    sponsors = _absolute_asset_paths(_load(SPONSORS_PATH), "logo")
    team = _absolute_team_paths(_load(TEAM_PATH))
    generator = LiveryGenerator(BASE_PATH, slots, working_scale=1, output_mode="RGB")
    _write_mask_previews(slots)

    palette = (
        (17, 104, 184),
        (220, 67, 67),
        (20, 150, 110),
        (148, 82, 184),
        (230, 143, 35),
        (28, 142, 164),
    )
    with tempfile.TemporaryDirectory(prefix="f2002_slot_labels_") as directory:
        label_directory = Path(directory)
        diagnostic_sponsors: dict[str, Any] = {}
        diagnostic_assignments: dict[str, str] = {}
        for index, slot_name in enumerate(slots):
            label_id = f"diagnostic_{index:02d}"
            label_path = label_directory / f"{label_id}.png"
            label_text = f"{slot_name.upper()}  →"
            _label_image(label_text, palette[index % len(palette)]).save(label_path)
            diagnostic_sponsors[label_id] = {"logo": str(label_path)}
            diagnostic_assignments[slot_name] = label_id

        generator.generate(
            diagnostic_assignments,
            diagnostic_sponsors,
            DIAGNOSTIC_OUTPUT,
            team_data=team,
        )

    unknown_slots = sorted(set(assignments) - set(slots))
    unknown_sponsors = sorted(set(assignments.values()) - set(sponsors))
    if unknown_slots or unknown_sponsors:
        raise KeyError(
            f"Invalid example assignments; slots={unknown_slots}, "
            f"sponsors={unknown_sponsors}"
        )
    generator.generate(assignments, sponsors, EXAMPLE_OUTPUT, team_data=team)
    print(f"Diagnostic livery: {DIAGNOSTIC_OUTPUT}")
    print(f"Example team livery: {EXAMPLE_OUTPUT}")


if __name__ == "__main__":
    main()

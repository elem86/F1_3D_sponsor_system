from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "reference_extract_test" / "sponsor_slots_raw.json"
OUTPUT_PATH = PROJECT_ROOT / "config" / "sponsor_slots.json"
REQUIRED_FIELDS = ("object", "face_indices", "uv_bounds", "pixel_bounds")


def build_compact_slots(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Keep only the fields needed by the livery-generation pipeline."""
    compact_data: dict[str, Any] = {}

    for slot_name, slot_info in raw_data.items():
        if not isinstance(slot_info, dict):
            raise TypeError(f"Slot '{slot_name}' must contain a JSON object")

        missing = [field for field in REQUIRED_FIELDS if field not in slot_info]
        if missing:
            missing_fields = ", ".join(missing)
            raise KeyError(f"Slot '{slot_name}' is missing: {missing_fields}")

        compact_data[slot_name] = {
            field: slot_info[field] for field in REQUIRED_FIELDS
        }
        for optional_field in ("transform", "safe_area", "content_box", "padding"):
            if optional_field in slot_info:
                compact_data[slot_name][optional_field] = slot_info[optional_field]

    return compact_data


def main() -> None:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw slot file not found: {RAW_PATH}")

    with RAW_PATH.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    if not isinstance(raw_data, dict):
        raise TypeError("The raw slot file must contain a JSON object")

    compact_data = build_compact_slots(raw_data)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(compact_data, file, indent=4)
        file.write("\n")

    print(f"Created compact slot file: {OUTPUT_PATH}")
    print(f"Number of slots: {len(compact_data)}")
    for slot_name in compact_data:
        print(f" - {slot_name}")


if __name__ == "__main__":
    main()

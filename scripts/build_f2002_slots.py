from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_SLOTS_PATH = (
    PROJECT_ROOT / "config" / "models" / "f2002" / "sponsor_slots_raw.json"
)
PRODUCTION_SLOTS_PATH = (
    PROJECT_ROOT / "config" / "models" / "f2002" / "sponsor_slots.json"
)

# Blender labels are normalized only while compiling the runtime configuration.
NAME_NORMALIZATION = {
    "sidepods_left": "sidepod_left",
    "sidepods_right": "sidepod_right",
    "rearwing_left_endplater": "rearwing_left_endplate",
    "rearwing_right_endplater": "rearwing_right_endplate",
}

# This ordered definition also controls deterministic sponsor compositing order.
SLOTS_BY_TIER = {
    "A": (
        "sidepod_left",
        "sidepod_right",
        "engine_cover_left",
        "engine_cover_right",
        "rearwing_main",
    ),
    "B": (
        "nose_top",
        "nose_left",
        "nose_right",
        "frontwing_main",
    ),
    "C": (
        "frontwing_left_endplate",
        "frontwing_right_endplate",
        "rearwing_left_endplate",
        "rearwing_right_endplate",
    ),
}

# All rectangles are normalized inside each slot's immutable pixel_bounds.
SPECIAL_LAYOUTS = {
    "nose_top": {
        "sponsor_area": {"x": 0.02, "y": 0.10, "width": 0.57, "height": 0.80},
        "reserved_areas": [
            {
                "asset": "wordmark",
                "feature": "branding",
                "area": {"x": 0.62, "y": 0.15, "width": 0.20, "height": 0.70},
                "padding": 6,
            },
            {
                "asset": "driver_number",
                "feature": "driver_number",
                "area": {"x": 0.84, "y": 0.08, "width": 0.14, "height": 0.84},
                "padding": 6,
                "transform": {"flip_x": False, "flip_y": False, "rotate": 180},
            },
        ],
    },
    "nose_left": {
        "sponsor_area": {"x": 0.02, "y": 0.10, "width": 0.72, "height": 0.80},
        "reserved_areas": [
            {
                "asset": "small_mark",
                "feature": "branding",
                "area": {"x": 0.78, "y": 0.15, "width": 0.20, "height": 0.70},
                "padding": 6,
            }
        ],
    },
    "nose_right": {
        "sponsor_area": {"x": 0.02, "y": 0.10, "width": 0.72, "height": 0.80},
        "reserved_areas": [
            {
                "asset": "small_mark",
                "feature": "branding",
                "area": {"x": 0.78, "y": 0.15, "width": 0.20, "height": 0.70},
                "padding": 6,
            }
        ],
    },
}


def _load_object(path: Path) -> dict[str, Any]:
    """Load a JSON object with a focused schema error."""
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object in {path}")
    return value


def _copy_rectangle(
    value: Any, *, fields: tuple[str, ...], description: str
) -> dict[str, int | float]:
    """Copy only expected numeric rectangle fields from the Blender export."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{description} must be a JSON object")
    rectangle: dict[str, int | float] = {}
    for field in fields:
        number = value.get(field)
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise TypeError(f"{description}.{field} must be numeric")
        rectangle[field] = number
    return rectangle


def _build_mask(raw_slot: Mapping[str, Any], bounds: Mapping[str, Any]) -> dict[str, Any]:
    """Convert verbose absolute face polygons into compact slot-local arrays."""
    faces = raw_slot.get("faces")
    if not isinstance(faces, list) or not faces:
        raise ValueError("Raw slot must contain selected face polygons")
    polygons: list[list[list[float]]] = []
    for face in faces:
        if not isinstance(face, Mapping):
            raise TypeError("Raw face entry must be a JSON object")
        pixel_polygon = face.get("pixel_polygon")
        if not isinstance(pixel_polygon, list) or len(pixel_polygon) < 3:
            raise ValueError("Raw face must contain a pixel polygon")
        polygon: list[list[float]] = []
        for point in pixel_polygon:
            if not isinstance(point, Mapping):
                raise TypeError("Raw polygon point must be a JSON object")
            polygon.append(
                [
                    round(float(point["x"]) - float(bounds["x"]), 2),
                    round(float(point["y"]) - float(bounds["y"]), 2),
                ]
            )
        polygons.append(polygon)
    return {"coordinate_space": "slot_local", "polygons": polygons}


def build_slots(raw_slots: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize Blender records into the compact runtime placement schema."""
    normalized: dict[str, Any] = {}
    for raw_name, raw_slot in raw_slots.items():
        slot_name = NAME_NORMALIZATION.get(raw_name, raw_name)
        if slot_name in normalized:
            raise ValueError(f"Duplicate normalized slot name: {slot_name}")
        normalized[slot_name] = raw_slot

    expected = {name for names in SLOTS_BY_TIER.values() for name in names}
    missing = sorted(expected - set(normalized))
    unexpected = sorted(set(normalized) - expected)
    if missing or unexpected:
        raise ValueError(
            f"Raw slot set mismatch; missing={missing or 'none'}, "
            f"unexpected={unexpected or 'none'}"
        )

    production: dict[str, Any] = {}
    for tier, slot_names in SLOTS_BY_TIER.items():
        for slot_name in slot_names:
            raw_slot = normalized[slot_name]
            if not isinstance(raw_slot, Mapping):
                raise TypeError(f"Raw slot {slot_name!r} must be a JSON object")
            object_name = raw_slot.get("object")
            if not isinstance(object_name, str) or not object_name:
                raise ValueError(f"Raw slot {slot_name!r} has no object name")

            # Face lists and per-face polygons remain in the immutable raw file.
            pixel_bounds = _copy_rectangle(
                raw_slot.get("pixel_bounds"),
                fields=("x", "y", "width", "height"),
                description=f"{slot_name}.pixel_bounds",
            )
            face_indices = raw_slot.get("face_indices")
            if not isinstance(face_indices, list) or not all(
                isinstance(index, int) and not isinstance(index, bool)
                for index in face_indices
            ):
                raise TypeError(f"{slot_name}.face_indices must be an integer list")
            slot: dict[str, Any] = {
                "name": slot_name,
                "tier": tier,
                "object": object_name,
                "pixel_bounds": pixel_bounds,
                "uv_bounds": _copy_rectangle(
                    raw_slot.get("uv_bounds"),
                    fields=("u_min", "u_max", "v_min", "v_max"),
                    description=f"{slot_name}.uv_bounds",
                ),
                "face_indices": face_indices,
                "mask": _build_mask(raw_slot, pixel_bounds),
                "mask_inset_px": {"A": 10, "B": 8, "C": 3}[tier],
                "transform": {"flip_x": False, "flip_y": False, "rotate": 0},
                "padding": {"A": 8, "B": 6, "C": 3}[tier],
            }
            if slot_name in SPECIAL_LAYOUTS:
                slot["layout"] = SPECIAL_LAYOUTS[slot_name]
            production[slot_name] = slot

    return production


def main() -> None:
    raw_slots = _load_object(RAW_SLOTS_PATH)
    production = build_slots(raw_slots)
    PRODUCTION_SLOTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PRODUCTION_SLOTS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(production, handle, indent=4)
        handle.write("\n")

    print(f"Raw slots: {len(raw_slots)} from {RAW_SLOTS_PATH}")
    print(f"Production slots: {len(production)} -> {PRODUCTION_SLOTS_PATH}")
    for name, slot in production.items():
        print(f"  {name}: tier {slot['tier']} -> {slot['pixel_bounds']}")


if __name__ == "__main__":
    main()

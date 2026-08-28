from __future__ import annotations

import math
from typing import Any, Mapping

from PIL import Image, ImageDraw, ImageFilter


def rasterize_slot_mask(slot: Mapping[str, Any]) -> Image.Image | None:
    """Rasterize the union of a slot's Blender-selected face polygons."""
    mask_config = slot.get("mask")
    if mask_config is None:
        return None
    if not isinstance(mask_config, Mapping):
        raise TypeError("Slot mask must be a JSON object")
    if mask_config.get("coordinate_space") != "slot_local":
        raise ValueError("Slot mask coordinate_space must be 'slot_local'")

    bounds = slot.get("pixel_bounds", slot)
    width = bounds["width"]
    height = bounds["height"]
    if not isinstance(width, int) or not isinstance(height, int):
        raise TypeError("Masked slot dimensions must be integers")
    if width <= 0 or height <= 0:
        raise ValueError("Masked slot dimensions must be positive")

    polygons = mask_config.get("polygons")
    if not isinstance(polygons, list) or not polygons:
        raise ValueError("Slot mask must contain at least one polygon")
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    for polygon in polygons:
        if not isinstance(polygon, list) or len(polygon) < 3:
            raise ValueError("Every slot mask polygon needs at least three points")
        points: list[tuple[int, int]] = []
        for point in polygon:
            if (
                not isinstance(point, list)
                or len(point) != 2
                or any(
                    isinstance(value, bool) or not isinstance(value, (int, float))
                    for value in point
                )
            ):
                raise TypeError("Mask polygon points must be numeric [x, y] pairs")
            points.append((round(point[0]), round(point[1])))
        draw.polygon(points, fill=255)
    return mask


def _safe_area_rectangle(
    slot: Mapping[str, Any], size: tuple[int, int]
) -> tuple[int, int, int, int]:
    """Resolve the existing normalized safe-area schema in slot-local pixels."""
    safe_area = slot.get("safe_area", slot.get("content_box"))
    if safe_area is None:
        return 0, 0, size[0], size[1]
    if not isinstance(safe_area, Mapping):
        raise TypeError("Slot safe area must be a JSON object")

    values: dict[str, float] = {}
    for field, default in (
        ("x", 0.0),
        ("y", 0.0),
        ("width", 1.0),
        ("height", 1.0),
    ):
        value = safe_area.get(field, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"safe_area.{field} must be numeric")
        if not math.isfinite(value):
            raise ValueError(f"safe_area.{field} must be finite")
        values[field] = float(value)
    if (
        values["x"] < 0
        or values["y"] < 0
        or values["width"] <= 0
        or values["height"] <= 0
        or values["x"] + values["width"] > 1
        or values["y"] + values["height"] > 1
    ):
        raise ValueError("safe_area must remain inside normalized slot bounds")

    left = math.ceil(values["x"] * size[0])
    top = math.ceil(values["y"] * size[1])
    right = math.floor((values["x"] + values["width"]) * size[0])
    bottom = math.floor((values["y"] + values["height"]) * size[1])
    if right <= left or bottom <= top:
        raise ValueError("safe_area resolves to an empty mask rectangle")
    return left, top, right, bottom


def prepare_slot_mask(slot: Mapping[str, Any]) -> Image.Image | None:
    """Intersect a raw face mask with safe-area metadata and erode its edges."""
    mask = rasterize_slot_mask(slot)
    if mask is None:
        return None

    left, top, right, bottom = _safe_area_rectangle(slot, mask.size)
    safe_mask = Image.new("L", mask.size, 0)
    safe_mask.paste(255, (left, top, right, bottom))
    # Multiplication is an exact intersection because both inputs are binary.
    mask = Image.eval(mask, lambda value: 255 if value else 0)
    mask = Image.composite(mask, Image.new("L", mask.size, 0), safe_mask)

    inset = slot.get("mask_inset_px", 0)
    if isinstance(inset, bool) or not isinstance(inset, int):
        raise TypeError("mask_inset_px must be an integer")
    if inset < 0:
        raise ValueError("mask_inset_px cannot be negative")
    if inset:
        mask = mask.filter(ImageFilter.MinFilter(inset * 2 + 1))
    if mask.getbbox() is None:
        raise ValueError("Slot mask became empty after safe-area/inset processing")
    return mask


def largest_mask_rectangle(mask: Image.Image) -> tuple[int, int, int, int]:
    """Return the largest axis-aligned rectangle fully contained in a mask."""
    if mask.mode != "L":
        raise ValueError("largest_mask_rectangle expects an L-mode mask")
    width, height = mask.size
    pixels = mask.load()
    heights = [0] * width
    best_area = 0
    best = (0, 0, 0, 0)

    # A monotonic histogram stack finds the largest all-white rectangle in O(wh).
    for y in range(height):
        for x in range(width):
            heights[x] = heights[x] + 1 if pixels[x, y] else 0
        stack: list[tuple[int, int]] = []
        for x in range(width + 1):
            current_height = heights[x] if x < width else 0
            start = x
            while stack and stack[-1][1] > current_height:
                start_index, rectangle_height = stack.pop()
                area = rectangle_height * (x - start_index)
                if area > best_area:
                    best_area = area
                    best = (
                        start_index,
                        y - rectangle_height + 1,
                        x - start_index,
                        rectangle_height,
                    )
                start = start_index
            if current_height and (
                not stack or stack[-1][1] < current_height
            ):
                stack.append((start, current_height))

    if best_area == 0:
        raise ValueError("Slot mask contains no usable rectangle")
    return best


def best_mask_fit_rectangle(
    mask: Image.Image,
    aspect_ratio: float,
    padding: int = 0,
) -> tuple[int, int, int, int]:
    """Choose the contained rectangle that yields the largest fitted image."""
    if mask.mode != "L":
        raise ValueError("best_mask_fit_rectangle expects an L-mode mask")
    if not math.isfinite(aspect_ratio) or aspect_ratio <= 0:
        raise ValueError("Image aspect ratio must be positive and finite")
    if isinstance(padding, bool) or not isinstance(padding, int) or padding < 0:
        raise ValueError("Mask-fit padding must be a non-negative integer")

    width, height = mask.size
    pixels = mask.load()
    heights = [0] * width
    best_score = 0
    best_container_area = 0
    best = (0, 0, 0, 0)

    # Histogram rectangles describe every maximal all-mask container. Score each
    # by the aspect-preserving image area it can actually hold after padding.
    for y in range(height):
        for x in range(width):
            heights[x] = heights[x] + 1 if pixels[x, y] else 0
        stack: list[tuple[int, int]] = []
        for x in range(width + 1):
            current_height = heights[x] if x < width else 0
            start = x
            while stack and stack[-1][1] > current_height:
                start_index, container_height = stack.pop()
                container_width = x - start_index
                available_width = container_width - padding * 2
                available_height = container_height - padding * 2
                if available_width > 0 and available_height > 0:
                    fitted_width = min(
                        available_width,
                        math.floor(available_height * aspect_ratio),
                    )
                    fitted_height = min(
                        available_height,
                        math.floor(available_width / aspect_ratio),
                    )
                    score = fitted_width * fitted_height
                    container_area = container_width * container_height
                    if score > best_score or (
                        score == best_score and container_area > best_container_area
                    ):
                        best_score = score
                        best_container_area = container_area
                        best = (
                            start_index,
                            y - container_height + 1,
                            container_width,
                            container_height,
                        )
                start = start_index
            if current_height and (
                not stack or stack[-1][1] < current_height
            ):
                stack.append((start, current_height))

    if best_score == 0:
        raise ValueError("Slot mask cannot fit the transformed image")
    return best

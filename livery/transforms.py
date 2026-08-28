from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from PIL import Image, ImageChops

from livery.slot_masks import best_mask_fit_rectangle, prepare_slot_mask


@dataclass(frozen=True)
class SlotTransform:
    """Image transforms applied in flip-X, flip-Y, rotation order."""

    flip_x: bool = False
    flip_y: bool = False
    rotate: int = 0

    @classmethod
    def from_slot(cls, slot: Mapping[str, Any]) -> SlotTransform:
        raw_transform = slot.get("transform")
        if raw_transform is None:
            return cls()
        if not isinstance(raw_transform, Mapping):
            raise TypeError("Slot 'transform' must be a JSON object")

        flip_x = raw_transform.get("flip_x", False)
        flip_y = raw_transform.get("flip_y", False)
        rotate = raw_transform.get("rotate", 0)

        if not isinstance(flip_x, bool):
            raise TypeError("transform.flip_x must be a boolean")
        if not isinstance(flip_y, bool):
            raise TypeError("transform.flip_y must be a boolean")
        if isinstance(rotate, bool) or not isinstance(rotate, int):
            raise TypeError("transform.rotate must be an integer number of degrees")

        return cls(flip_x=flip_x, flip_y=flip_y, rotate=rotate % 360)


@dataclass(frozen=True)
class SlotPlacement:
    transform: SlotTransform
    transformed_size: tuple[int, int]
    fitted_size: tuple[int, int]
    destination_bounds: tuple[int, int, int, int]
    content_bounds: tuple[int, int, int, int]
    paste_position: tuple[int, int]
    padding: int


def apply_slot_transform(image: Image.Image, slot: Mapping[str, Any]) -> Image.Image:
    """Return a transformed copy of an image for the supplied sponsor slot.

    Positive rotation values follow Pillow's convention and rotate
    counter-clockwise. The canvas expands so rotated content is not cropped.
    """
    transform = SlotTransform.from_slot(slot)
    result = image.copy()

    if transform.flip_x:
        result = result.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if transform.flip_y:
        result = result.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if transform.rotate:
        result = result.rotate(
            transform.rotate,
            expand=True,
            resample=Image.Resampling.BICUBIC,
        )

    return result


def resolve_content_bounds(slot: Mapping[str, Any]) -> tuple[int, int, int, int]:
    """Resolve a normalized safe area to absolute pixel coordinates."""
    bounds = slot.get("pixel_bounds", slot)
    slot_x = bounds["x"]
    slot_y = bounds["y"]
    slot_width = bounds["width"]
    slot_height = bounds["height"]

    safe_area = slot.get("safe_area")
    content_box = slot.get("content_box")
    if safe_area is not None and content_box is not None:
        raise ValueError("Use either 'safe_area' or 'content_box', not both")

    normalized = safe_area if safe_area is not None else content_box
    if normalized is None:
        normalized = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
    if not isinstance(normalized, Mapping):
        raise TypeError("Slot safe area must be a JSON object")

    values: dict[str, float] = {}
    for field, default in (
        ("x", 0.0),
        ("y", 0.0),
        ("width", 1.0),
        ("height", 1.0),
    ):
        value = normalized.get(field, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"safe_area.{field} must be a number")
        if not math.isfinite(value):
            raise ValueError(f"safe_area.{field} must be finite")
        values[field] = float(value)

    safe_x = values["x"]
    safe_y = values["y"]
    safe_width = values["width"]
    safe_height = values["height"]
    if safe_x < 0 or safe_y < 0 or safe_width <= 0 or safe_height <= 0:
        raise ValueError("safe_area must have non-negative x/y and positive size")
    if safe_x + safe_width > 1 or safe_y + safe_height > 1:
        raise ValueError("safe_area must stay within normalized slot bounds")

    # Round inward so the resolved content box never extends beyond the
    # requested normalized safe area.
    left = slot_x + math.ceil(safe_x * slot_width)
    top = slot_y + math.ceil(safe_y * slot_height)
    right = slot_x + math.floor((safe_x + safe_width) * slot_width)
    bottom = slot_y + math.floor((safe_y + safe_height) * slot_height)
    if right <= left or bottom <= top:
        raise ValueError("safe_area resolves to an empty pixel rectangle")

    return left, top, right - left, bottom - top


def composite_slot_image(
    canvas: Image.Image,
    image: Image.Image,
    slot: Mapping[str, Any],
    *,
    preferred_padding: int | None = None,
) -> SlotPlacement:
    """Transform, proportionally fit, center, and composite an image in a slot."""
    bounds = slot.get("pixel_bounds", slot)
    x = bounds["x"]
    y = bounds["y"]
    width = bounds["width"]
    height = bounds["height"]

    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid slot dimensions: {bounds}")
    requested_padding = (
        slot.get("padding", 0) if preferred_padding is None else preferred_padding
    )
    if isinstance(requested_padding, bool) or not isinstance(requested_padding, int):
        raise TypeError("Slot padding must be an integer")
    if requested_padding < 0:
        raise ValueError("Slot padding cannot be negative")

    transform = SlotTransform.from_slot(slot)
    transformed = apply_slot_transform(image, slot)
    transformed_size = transformed.size

    # Crop to the visible non-transparent bounds so centering reflects what the
    # viewer actually sees, not incidental transparent margins in the source PNG.
    visible_bbox = transformed.getbbox()
    visible = transformed.crop(visible_bbox) if visible_bbox else transformed

    center_on_visible_mask = slot.get("center_on_visible_mask", False)
    if isinstance(center_on_visible_mask, bool):
        pass
    else:
        raise TypeError("Slot center_on_visible_mask must be a boolean")

    prepared_mask = prepare_slot_mask(slot)
    if prepared_mask is None:
        content_x, content_y, content_width, content_height = resolve_content_bounds(
            slot
        )
        center_x, center_y = content_x, content_y
        center_width, center_height = content_width, content_height
    else:
        local_x, local_y, content_width, content_height = best_mask_fit_rectangle(
            prepared_mask,
            visible.width / visible.height,
            requested_padding,
        )
        content_x = x + local_x
        content_y = y + local_y
        if center_on_visible_mask:
            # Size against the largest contained rectangle (preserves existing
            # sponsor sizing), but center within the mask's full visible
            # footprint so an off-center contained rectangle can't drag the
            # logo off-center. Opt-in only: most masks are already centered
            # via their largest contained rectangle, and this must not shift
            # those known-good placements.
            mask_bbox = prepared_mask.getbbox()
            center_x = x + mask_bbox[0]
            center_y = y + mask_bbox[1]
            center_width = mask_bbox[2] - mask_bbox[0]
            center_height = mask_bbox[3] - mask_bbox[1]
        else:
            center_x, center_y = content_x, content_y
            center_width, center_height = content_width, content_height

    # Keep two pixels where the content box is large enough, one on small boxes,
    # and zero only when even a one-pixel margin would leave no drawable area.
    padding = min(
        requested_padding,
        (content_width - 1) // 2,
        (content_height - 1) // 2,
    )
    available_width = content_width - padding * 2
    available_height = content_height - padding * 2

    scale = min(
        available_width / visible.width,
        available_height / visible.height,
    )
    fitted_size = (
        max(1, int(visible.width * scale)),
        max(1, int(visible.height * scale)),
    )
    fitted = visible.resize(fitted_size, Image.Resampling.LANCZOS)

    paste_x = center_x + (center_width - fitted.width) // 2
    paste_y = center_y + (center_height - fitted.height) // 2
    if prepared_mask is None:
        canvas.alpha_composite(fitted, (paste_x, paste_y))
    else:
        # Compose through the eroded face-union mask as a final guarantee that
        # no texture pixels can reach unselected neighboring UV islands.
        local_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        local_layer.alpha_composite(fitted, (paste_x - x, paste_y - y))
        clipped_alpha = ImageChops.multiply(
            local_layer.getchannel("A"), prepared_mask
        )
        local_layer.putalpha(clipped_alpha)
        canvas.alpha_composite(local_layer, (x, y))

    return SlotPlacement(
        transform=transform,
        transformed_size=transformed_size,
        fitted_size=fitted_size,
        destination_bounds=(x, y, width, height),
        content_bounds=(content_x, content_y, content_width, content_height),
        paste_position=(paste_x, paste_y),
        padding=padding,
    )

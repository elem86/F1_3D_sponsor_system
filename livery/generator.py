from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PIL import Image

from livery.transforms import SlotPlacement, composite_slot_image


class LiveryGenerator:
    """
    Generates a car livery texture by placing sponsor logos
    onto a base texture according to predefined slot coordinates.
    """

    def __init__(
        self,
        base_texture_path: str | Path,
        slots: Dict[str, Any],
        working_scale: int = 4,
    ):
        """
        Parameters
        ----------
        base_texture_path : str | Path
            Path to the blank/base car texture.
        slots : dict
            Slot configuration loaded from sponsor_slots.json.
        """
        self.base_texture_path = Path(base_texture_path)
        self.slots = slots
        self.working_scale = working_scale

        if not self.base_texture_path.exists():
            raise FileNotFoundError(f"Base texture not found: {self.base_texture_path}")
        if isinstance(working_scale, bool) or not isinstance(working_scale, int):
            raise TypeError("working_scale must be an integer")
        if working_scale < 1:
            raise ValueError("working_scale must be at least 1")

    @staticmethod
    def _scale_slot(slot: Dict[str, Any], scale: int) -> Dict[str, Any]:
        """Scale pixel-space slot fields without changing calibration data."""
        scaled_slot = dict(slot)
        bounds = slot.get("pixel_bounds", slot)
        scaled_bounds = {
            "x": bounds["x"] * scale,
            "y": bounds["y"] * scale,
            "width": bounds["width"] * scale,
            "height": bounds["height"] * scale,
        }
        if "pixel_bounds" in slot:
            scaled_slot["pixel_bounds"] = scaled_bounds
        else:
            scaled_slot.update(scaled_bounds)

        if "padding" in slot:
            scaled_slot["padding"] = slot["padding"] * scale

        return scaled_slot

    @staticmethod
    def _place_logo(
        canvas: Image.Image, logo_path: str | Path, slot: Dict[str, Any]
    ) -> tuple[SlotPlacement, tuple[int, int]]:
        """
        Place a logo onto the canvas at the specified slot.
        """
        logo_path = Path(logo_path)

        if not logo_path.exists():
            raise FileNotFoundError(f"Logo not found: {logo_path}")

        with Image.open(logo_path) as source:
            # RGBA conversion retains transparency from sponsor PNGs.
            logo = source.convert("RGBA")
        source_size = logo.size

        placement = composite_slot_image(canvas, logo, slot)
        return placement, source_size

    def generate(
        self,
        assignments: Dict[str, str],
        sponsor_data: Dict[str, Any],
        output_path: str | Path,
    ) -> Path:
        """
        Generate a livery texture and save it to disk.

        Parameters
        ----------
        assignments : dict
            Maps slot names to sponsor names.
            Example:
                {
                    "left_sidepod": "Marlboro",
                    "rear_wing": "FedEx"
                }
        sponsor_data : dict
            Sponsor config loaded from sponsors.json.
        output_path : str | Path
            Where the generated texture should be saved.

        Returns
        -------
        Path
            Path to the generated texture file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # A final livery must never become the next generation's base image.
        if output_path.resolve() == self.base_texture_path.resolve():
            raise ValueError("Base texture and livery output paths must be different")

        with Image.open(self.base_texture_path) as source:
            base = source.convert("RGBA")

        final_size = base.size
        working_size = (
            final_size[0] * self.working_scale,
            final_size[1] * self.working_scale,
        )
        canvas = base.resize(working_size, Image.Resampling.LANCZOS)

        for slot_name in assignments:
            if slot_name not in self.slots:
                print(f"[WARNING] Unknown slot: {slot_name}")

        # Use calibrated slot order so identical assignment mappings always
        # composite in the same order, even after a slot is removed and re-added.
        for slot_name, slot in self.slots.items():
            if slot_name not in assignments:
                continue
            sponsor_name = assignments[slot_name]
            if sponsor_name not in sponsor_data:
                print(f"[WARNING] Unknown sponsor: {sponsor_name}")
                continue

            working_slot = self._scale_slot(slot, self.working_scale)
            logo_path = sponsor_data[sponsor_name]["logo"]

            placement, source_size = self._place_logo(
                canvas, logo_path, working_slot
            )
            transform = placement.transform
            safe_area = slot.get(
                "safe_area",
                {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
            )
            print(
                f"{slot_name} -> {sponsor_name} -> "
                f"transform=(flip_x={transform.flip_x}, "
                f"flip_y={transform.flip_y}, rotate={transform.rotate}) -> "
                f"safe_area={safe_area} -> "
                f"source={source_size[0]}x{source_size[1]} -> "
                f"transformed={placement.transformed_size[0]}x"
                f"{placement.transformed_size[1]} -> "
                f"fitted={placement.fitted_size[0]}x{placement.fitted_size[1]} -> "
                f"padding={placement.padding}"
            )

        final = canvas.resize(final_size, Image.Resampling.LANCZOS)
        final.save(output_path)
        print(
            f"Internal composition resolution: "
            f"{working_size[0]}x{working_size[1]}"
        )
        print(f"Final output resolution: {final_size[0]}x{final_size[1]}")
        return output_path

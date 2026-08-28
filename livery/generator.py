from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping

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
        output_mode: str = "RGBA",
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
        self.output_mode = output_mode

        if not self.base_texture_path.exists():
            raise FileNotFoundError(f"Base texture not found: {self.base_texture_path}")
        if isinstance(working_scale, bool) or not isinstance(working_scale, int):
            raise TypeError("working_scale must be an integer")
        if working_scale < 1:
            raise ValueError("working_scale must be at least 1")
        if output_mode not in {"RGB", "RGBA"}:
            raise ValueError("output_mode must be either 'RGB' or 'RGBA'")

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
        if "mask_inset_px" in slot:
            scaled_slot["mask_inset_px"] = slot["mask_inset_px"] * scale
        if "mask" in slot:
            mask = slot["mask"]
            if not isinstance(mask, Mapping):
                raise TypeError("Slot mask must be a JSON object")
            polygons = mask.get("polygons")
            if not isinstance(polygons, list):
                raise TypeError("Slot mask polygons must be a list")
            scaled_mask = dict(mask)
            scaled_mask["polygons"] = [
                [[point[0] * scale, point[1] * scale] for point in polygon]
                for polygon in polygons
            ]
            scaled_slot["mask"] = scaled_mask

        return scaled_slot

    @staticmethod
    def _sponsor_slot(slot: Mapping[str, Any]) -> Dict[str, Any]:
        """Apply an optional layout sponsor area without mutating calibration."""
        effective = dict(slot)
        layout = slot.get("layout")
        if layout is None:
            return effective
        if not isinstance(layout, Mapping):
            raise TypeError("Slot layout must be a JSON object")
        sponsor_area = layout.get("sponsor_area")
        if sponsor_area is None:
            return effective
        if "safe_area" in slot or "content_box" in slot:
            raise ValueError(
                "A slot with layout.sponsor_area cannot also define safe_area/content_box"
            )
        effective["safe_area"] = sponsor_area
        return effective

    @classmethod
    def _team_overlay_slot(
        cls,
        slot: Mapping[str, Any],
        reserved_area: Mapping[str, Any],
        scale: int,
    ) -> Dict[str, Any]:
        """Create a normal placement slot for one reserved branding rectangle."""
        area = reserved_area.get("area")
        if not isinstance(area, Mapping):
            raise TypeError("Reserved branding area must define an 'area' object")
        scaled_outer = cls._scale_slot(dict(slot), scale)
        padding = reserved_area.get("padding", 0)
        if isinstance(padding, bool) or not isinstance(padding, int):
            raise TypeError("Reserved branding padding must be an integer")
        if padding < 0:
            raise ValueError("Reserved branding padding cannot be negative")
        overlay: Dict[str, Any] = {
            "pixel_bounds": scaled_outer["pixel_bounds"],
            "safe_area": dict(area),
            "padding": padding * scale,
        }
        # Reserved content is constrained by the exact same selected-face mask.
        if "mask" in scaled_outer:
            overlay["mask"] = scaled_outer["mask"]
        if "mask_inset_px" in scaled_outer:
            overlay["mask_inset_px"] = scaled_outer["mask_inset_px"]
        transform = reserved_area.get("transform", slot.get("transform"))
        if transform is not None:
            overlay["transform"] = transform
        return overlay

    def _place_team_branding(
        self,
        canvas: Image.Image,
        team_data: Mapping[str, Any] | None,
    ) -> int:
        """Render configured built-in assets into reserved slot sub-areas."""
        if team_data is None:
            return 0
        assets = team_data.get("assets")
        if not isinstance(assets, Mapping):
            raise TypeError("Team identity must define an assets object")
        features = team_data.get("features", {})
        if not isinstance(features, Mapping):
            raise TypeError("Team identity features must be a JSON object")

        placed = 0
        for slot_name, slot in self.slots.items():
            layout = slot.get("layout")
            if layout is None:
                continue
            if not isinstance(layout, Mapping):
                raise TypeError(f"Slot {slot_name!r} layout must be an object")
            reserved_areas = layout.get("reserved_areas", [])
            if not isinstance(reserved_areas, list):
                raise TypeError(
                    f"Slot {slot_name!r} layout.reserved_areas must be a list"
                )
            for reserved_area in reserved_areas:
                if not isinstance(reserved_area, Mapping):
                    raise TypeError(
                        f"Slot {slot_name!r} contains an invalid reserved area"
                    )
                feature = reserved_area.get("feature", "branding")
                if not isinstance(feature, str):
                    raise TypeError("Reserved area feature must be a string")
                if not bool(features.get(feature, False)):
                    continue
                asset_id = reserved_area.get("asset")
                if not isinstance(asset_id, str) or asset_id not in assets:
                    raise KeyError(
                        f"Slot {slot_name!r} references unknown team asset {asset_id!r}"
                    )
                logo_path = assets[asset_id]
                if not isinstance(logo_path, (str, Path)):
                    raise TypeError(f"Team asset {asset_id!r} must be a path")
                overlay_slot = self._team_overlay_slot(
                    slot, reserved_area, self.working_scale
                )
                placement, source_size = self._place_logo(
                    canvas, logo_path, overlay_slot
                )
                print(
                    f"{slot_name} -> team:{asset_id} -> "
                    f"source={source_size[0]}x{source_size[1]} -> "
                    f"transformed={placement.transformed_size[0]}x"
                    f"{placement.transformed_size[1]} -> "
                    f"fitted={placement.fitted_size[0]}x{placement.fitted_size[1]}"
                )
                placed += 1
        return placed

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
        team_data: Mapping[str, Any] | None = None,
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
        # Avoid a redundant resampling pass when the source atlas is already at
        # the requested working resolution, as it is for the native 2024 atlas.
        canvas = (
            base.copy()
            if working_size == final_size
            else base.resize(working_size, Image.Resampling.LANCZOS)
        )

        # Built-in identity elements are rebuilt from configuration before the
        # independent sponsor layer is composed over the clean source atlas.
        team_placements = self._place_team_branding(canvas, team_data)

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

            sponsor_slot = self._sponsor_slot(slot)
            working_slot = self._scale_slot(sponsor_slot, self.working_scale)
            logo_path = sponsor_data[sponsor_name]["logo"]

            placement, source_size = self._place_logo(
                canvas, logo_path, working_slot
            )
            transform = placement.transform
            safe_area = sponsor_slot.get(
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

        final = (
            canvas
            if canvas.size == final_size
            else canvas.resize(final_size, Image.Resampling.LANCZOS)
        )
        # Composition uses RGBA internally, but models with an opaque atlas can
        # request RGB output so the saved file cannot accidentally turn clear.
        if final.mode != self.output_mode:
            final = final.convert(self.output_mode)
        # Save to a unique sibling first, then replace atomically. The viewer can
        # never observe a partially written 2024 PNG during a rapid refresh.
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{output_path.stem}_",
                suffix=output_path.suffix,
                dir=output_path.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            final.save(temporary_path, format="PNG")
            temporary_path.replace(output_path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
        print(
            f"Internal composition resolution: "
            f"{working_size[0]}x{working_size[1]}"
        )
        print(f"Final output resolution: {final_size[0]}x{final_size[1]}")
        print(f"Team branding placements: {team_placements}")
        return output_path

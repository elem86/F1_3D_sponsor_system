from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

from livery.generator import LiveryGenerator
from livery.slot_masks import rasterize_slot_mask


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class F2002LiveryTests(unittest.TestCase):
    """Protect mask clipping and clean-base rebuilding in the runtime pipeline."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.slots = _load(
            PROJECT_ROOT / "config" / "models" / "f2002" / "sponsor_slots.json"
        )
        cls.sponsors = _load(PROJECT_ROOT / "config" / "sponsors.json")
        for sponsor in cls.sponsors.values():
            sponsor["logo"] = str((PROJECT_ROOT / sponsor["logo"]).resolve())
        cls.team = _load(PROJECT_ROOT / "config" / "teams" / "default_team.json")
        cls.team["assets"] = {
            name: str((PROJECT_ROOT / path).resolve())
            for name, path in cls.team["assets"].items()
        }
        cls.base_path = PROJECT_ROOT / "assets" / "models" / "f2002" / "white_base.png"
        cls.temporary = tempfile.TemporaryDirectory(prefix="f2002_livery_tests_")
        cls.output_directory = Path(cls.temporary.name)
        cls.generator = LiveryGenerator(
            cls.base_path,
            cls.slots,
            working_scale=1,
            output_mode="RGB",
        )
        cls.baseline_path = cls.output_directory / "baseline.png"
        cls._render({}, cls.baseline_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    @classmethod
    def _render(
        cls,
        assignments: dict[str, str],
        output: Path,
        *,
        team: dict | None = None,
    ) -> None:
        # Keep per-placement reports out of routine test output.
        with contextlib.redirect_stdout(io.StringIO()):
            cls.generator.generate(
                assignments,
                cls.sponsors,
                output,
                team_data=cls.team if team is None else team,
            )

    @staticmethod
    def _rgb_difference(first: Image.Image, second: Image.Image) -> Image.Image:
        channels = ImageChops.difference(first, second).split()
        return ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])

    def test_every_slot_is_clipped_to_its_selected_face_mask(self) -> None:
        with Image.open(self.baseline_path) as baseline:
            baseline = baseline.copy()
        for slot_name, slot in self.slots.items():
            output = self.output_directory / f"mask_{slot_name}.png"
            self._render({slot_name: "veltrix"}, output)
            with Image.open(output) as rendered:
                difference = self._rgb_difference(baseline, rendered)

            bounds = slot["pixel_bounds"]
            box = (
                bounds["x"],
                bounds["y"],
                bounds["x"] + bounds["width"],
                bounds["y"] + bounds["height"],
            )
            difference_box = difference.getbbox()
            self.assertIsNotNone(difference_box, slot_name)
            self.assertGreaterEqual(difference_box[0], box[0], slot_name)
            self.assertGreaterEqual(difference_box[1], box[1], slot_name)
            self.assertLessEqual(difference_box[2], box[2], slot_name)
            self.assertLessEqual(difference_box[3], box[3], slot_name)

            raw_mask = rasterize_slot_mask(slot)
            self.assertIsNotNone(raw_mask, slot_name)
            outside_mask = ImageChops.multiply(
                difference.crop(box), ImageChops.invert(raw_mask)
            )
            self.assertIsNone(outside_mask.getbbox(), slot_name)

    def test_nose_sponsor_removal_rebuilds_the_overlay_only_baseline(self) -> None:
        applied = self.output_directory / "nose_applied.png"
        removed = self.output_directory / "nose_removed.png"
        self._render({"nose_top": "aeron"}, applied)
        self._render({}, removed)
        self.assertNotEqual(applied.read_bytes(), removed.read_bytes())
        self.assertEqual(self.baseline_path.read_bytes(), removed.read_bytes())

    def test_driver_number_can_be_disabled(self) -> None:
        disabled_team = dict(self.team)
        disabled_team["features"] = {
            **self.team.get("features", {}),
            "branding": False,
            "driver_number": False,
        }
        output = self.output_directory / "no_overlays.png"
        self._render({}, output, team=disabled_team)
        with Image.open(output) as rendered, Image.open(self.base_path) as base:
            self.assertIsNone(ImageChops.difference(rendered, base).getbbox())


if __name__ == "__main__":
    unittest.main()

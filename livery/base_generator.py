from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from PIL import Image


TEXTURE_SIZE = (256, 256)


def parse_hex_color(value: str) -> tuple[int, int, int]:
    """Convert a #RRGGBB team color to an RGB tuple."""
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        raise ValueError(f"Expected color in #RRGGBB format, got: {value!r}")

    try:
        return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))
    except ValueError as error:
        raise ValueError(f"Invalid hexadecimal color: {value!r}") from error


def generate_team_base(
    team_config: Mapping[str, Any], output_path: str | Path
) -> Path:
    """Generate a plain, fully opaque base texture from a team config."""
    colors = team_config.get("colors")
    if not isinstance(colors, Mapping) or "primary" not in colors:
        raise KeyError("Team config must define colors.primary")

    primary = parse_hex_color(colors["primary"])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base = Image.new("RGBA", TEXTURE_SIZE, primary + (255,))
    base.save(output_path)
    return output_path

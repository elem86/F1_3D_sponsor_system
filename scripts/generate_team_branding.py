from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEAM_PATH = PROJECT_ROOT / "config" / "teams" / "default_team.json"
OUTPUT_DIRECTORY = PROJECT_ROOT / "assets" / "branding" / "default_team"
RGBA = tuple[int, int, int, int]
Renderer = Callable[[dict], Image.Image]


def _font(size: int, *, italic: bool = False) -> ImageFont.ImageFont:
    """Use a bundled system font when available and a Pillow fallback otherwise."""
    font_directory = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    names = ("arialbi.ttf", "calibriz.ttf") if italic else ("arialbd.ttf", "calibrib.ttf")
    for candidate in [*(font_directory / name for name in names), *map(Path, names)]:
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex_color(value: str) -> RGBA:
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        raise ValueError(f"Expected #RRGGBB color, received {value!r}")
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5)) + (255,)


def _finish(canvas: Image.Image, output_path: Path, maximum: tuple[int, int]) -> None:
    """Tightly crop a transparent source while retaining a small clear margin."""
    bounds = canvas.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError(f"Branding renderer produced no pixels: {output_path.name}")
    cropped = canvas.crop(bounds)
    padding = 24
    scale = min(
        (maximum[0] - padding * 2) / cropped.width,
        (maximum[1] - padding * 2) / cropped.height,
        1.0,
    )
    size = (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale)))
    if size != cropped.size:
        cropped = cropped.resize(size, Image.Resampling.LANCZOS)
    output = Image.new("RGBA", (cropped.width + padding * 2, cropped.height + padding * 2))
    output.alpha_composite(cropped, (padding, padding))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path, format="PNG")


def _wordmark(team: dict) -> Image.Image:
    primary = _hex_color(team["colors"]["primary"])
    accent = _hex_color(team["colors"]["accent"])
    canvas = Image.new("RGBA", (1900, 500))
    draw = ImageDraw.Draw(canvas)
    # The asymmetric three-stripe wing makes mirrored UV placement obvious.
    draw.polygon(((45, 245), (300, 70), (220, 245)), fill=accent)
    draw.polygon(((80, 300), (330, 130), (260, 300)), fill=primary)
    draw.polygon(((125, 355), (360, 205), (305, 355)), fill=accent)
    draw.text(
        (390, 250),
        team["name"],
        font=_font(275, italic=True),
        anchor="lm",
        fill=primary,
        stroke_width=5,
        stroke_fill=(255, 255, 255, 220),
    )
    draw.polygon(((1715, 95), (1835, 95), (1755, 390), (1635, 390)), fill=accent)
    return canvas


def _small_mark(team: dict) -> Image.Image:
    primary = _hex_color(team["colors"]["primary"])
    accent = _hex_color(team["colors"]["accent"])
    canvas = Image.new("RGBA", (720, 720))
    draw = ImageDraw.Draw(canvas)
    draw.polygon(((90, 610), (320, 80), (425, 80), (225, 610)), fill=primary)
    draw.polygon(((395, 80), (650, 610), (515, 610), (355, 250)), fill=accent)
    draw.polygon(((225, 430), (505, 430), (550, 535), (180, 535)), fill=primary)
    draw.polygon(((470, 120), (650, 120), (590, 250), (440, 250)), fill=accent)
    return canvas


def _driver_number(team: dict) -> Image.Image:
    primary = _hex_color(team["colors"]["primary"])
    accent = _hex_color(team["colors"]["accent"])
    canvas = Image.new("RGBA", (650, 900))
    draw = ImageDraw.Draw(canvas)
    number = str(team["driver_number"])
    draw.text(
        (325, 465),
        number,
        font=_font(720, italic=True),
        anchor="mm",
        fill=primary,
        stroke_width=24,
        stroke_fill=accent,
    )
    draw.polygon(((115, 785), (545, 785), (500, 850), (70, 850)), fill=accent)
    return canvas


def _validate(path: Path) -> None:
    with Image.open(path) as image:
        if image.mode != "RGBA" or image.getchannel("A").getbbox() is None:
            raise ValueError(f"Invalid transparent branding asset: {path}")
        if image.getchannel("A").getextrema()[0] != 0:
            raise ValueError(f"Branding asset has no transparent pixels: {path}")


def main() -> None:
    with TEAM_PATH.open("r", encoding="utf-8") as handle:
        team = json.load(handle)
    renderers: dict[str, tuple[Renderer, tuple[int, int]]] = {
        "aeron_wordmark.png": (_wordmark, (1600, 420)),
        "aeron_small.png": (_small_mark, (640, 640)),
        "number_1.png": (_driver_number, (512, 768)),
    }
    for filename, (renderer, maximum) in renderers.items():
        output = OUTPUT_DIRECTORY / filename
        _finish(renderer(team), output, maximum)
        _validate(output)
        with Image.open(output) as image:
            print(f"Generated {output}: {image.mode} {image.size}")


if __name__ == "__main__":
    main()

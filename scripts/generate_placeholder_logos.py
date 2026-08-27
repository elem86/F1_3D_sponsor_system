from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "assets" / "logos"
MAX_OUTPUT_SIZE = (1024, 512)
OUTPUT_PADDING = 28

RGBA = tuple[int, int, int, int]
Renderer = Callable[[], Image.Image]


def load_font(size: int, *, italic: bool = False) -> ImageFont.ImageFont:
    windows_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    names = (
        ("arialbi.ttf", "calibriz.ttf", "DejaVuSansCondensed-Oblique.ttf")
        if italic
        else ("arialbd.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf")
    )
    candidates = [windows_fonts / name for name in names]
    candidates.extend(Path(name) for name in names)

    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue

    return ImageFont.load_default()


def hexagon(center: tuple[int, int], radius: int) -> list[tuple[int, int]]:
    cx, cy = center
    return [
        (
            round(cx + radius * math.cos(math.radians(60 * index - 30))),
            round(cy + radius * math.sin(math.radians(60 * index - 30))),
        )
        for index in range(6)
    ]


def finalize_logo(canvas: Image.Image, output_path: Path) -> None:
    alpha_bounds = canvas.getchannel("A").getbbox()
    if alpha_bounds is None:
        raise ValueError(f"Logo renderer produced an empty image: {output_path.stem}")

    cropped = canvas.crop(alpha_bounds)
    available_width = MAX_OUTPUT_SIZE[0] - OUTPUT_PADDING * 2
    available_height = MAX_OUTPUT_SIZE[1] - OUTPUT_PADDING * 2
    scale = min(
        available_width / cropped.width,
        available_height / cropped.height,
    )
    fitted_size = (
        max(1, round(cropped.width * scale)),
        max(1, round(cropped.height * scale)),
    )
    fitted = cropped.resize(fitted_size, Image.Resampling.LANCZOS)

    output = Image.new(
        "RGBA",
        (fitted.width + OUTPUT_PADDING * 2, fitted.height + OUTPUT_PADDING * 2),
        (0, 0, 0, 0),
    )
    output.alpha_composite(fitted, (OUTPUT_PADDING, OUTPUT_PADDING))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path)


def render_veltrix() -> Image.Image:
    canvas = Image.new("RGBA", (1500, 380), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cyan: RGBA = (35, 225, 255, 255)
    white: RGBA = (250, 250, 255, 255)
    dark: RGBA = (10, 18, 30, 255)

    draw.polygon(((35, 65), (155, 315), (245, 65), (180, 65), (150, 190), (105, 65)), fill=cyan)
    draw.polygon(((155, 315), (270, 165), (230, 315)), fill=white)
    draw.text(
        (300, 185),
        "VELTRIX",
        font=load_font(170, italic=True),
        anchor="lm",
        fill=white,
        stroke_width=9,
        stroke_fill=dark,
    )
    draw.polygon(((1330, 70), (1415, 70), (1360, 310), (1275, 310)), fill=cyan)
    return canvas


def render_nordyn() -> Image.Image:
    canvas = Image.new("RGBA", (760, 700), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    blue: RGBA = (80, 155, 255, 255)
    ice: RGBA = (225, 245, 255, 255)
    dark: RGBA = (12, 25, 48, 255)

    outer = hexagon((380, 245), 190)
    inner = hexagon((380, 245), 145)
    draw.line(outer + [outer[0]], fill=blue, width=34, joint="curve")
    draw.line(inner + [inner[0]], fill=ice, width=12, joint="curve")
    draw.polygon(((285, 330), (285, 155), (340, 155), (465, 330), (465, 155), (520, 155), (520, 330), (465, 330), (340, 155), (340, 330)), fill=blue)
    draw.polygon(((510, 90), (575, 125), (520, 165)), fill=ice)
    draw.text(
        (380, 565),
        "NORDYN",
        font=load_font(125),
        anchor="mm",
        fill=ice,
        stroke_width=8,
        stroke_fill=dark,
    )
    return canvas


def render_kinetra() -> Image.Image:
    canvas = Image.new("RGBA", (1750, 390), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    lime: RGBA = (160, 255, 55, 255)
    white: RGBA = (250, 255, 245, 255)
    dark: RGBA = (20, 30, 12, 255)

    draw.polygon(((20, 190), (190, 55), (190, 135), (330, 135), (330, 245), (190, 245), (190, 325)), fill=lime)
    draw.line((40, 80, 165, 80), fill=white, width=24)
    draw.line((40, 300, 165, 300), fill=white, width=24)
    draw.text(
        (360, 195),
        "KINETRA",
        font=load_font(175, italic=True),
        anchor="lm",
        fill=white,
        stroke_width=9,
        stroke_fill=dark,
    )
    draw.polygon(((1530, 80), (1725, 195), (1530, 310), (1580, 220), (1455, 220), (1455, 170), (1580, 170)), fill=lime)
    return canvas


def render_orbix() -> Image.Image:
    canvas = Image.new("RGBA", (760, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    violet: RGBA = (190, 95, 255, 255)
    gold: RGBA = (255, 205, 60, 255)
    white: RGBA = (250, 245, 255, 255)
    dark: RGBA = (28, 14, 45, 255)

    draw.ellipse((165, 55, 595, 465), outline=violet, width=38)
    draw.ellipse((110, 150, 650, 370), outline=white, width=22)
    draw.ellipse((315, 165, 445, 295), fill=violet)
    draw.ellipse((525, 105, 605, 185), fill=gold)
    draw.polygon(((590, 370), (680, 405), (605, 455)), fill=gold)
    draw.text(
        (380, 590),
        "ORBIX",
        font=load_font(145),
        anchor="mm",
        fill=white,
        stroke_width=9,
        stroke_fill=dark,
    )
    return canvas


def render_aeron() -> Image.Image:
    canvas = Image.new("RGBA", (1550, 430), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    sky: RGBA = (70, 220, 255, 255)
    white: RGBA = (250, 255, 255, 255)
    dark: RGBA = (8, 28, 38, 255)

    draw.polygon(((25, 220), (300, 45), (235, 175), (390, 175), (390, 225), (210, 225), (145, 350)), fill=sky)
    draw.polygon(((75, 300), (250, 245), (360, 245), (310, 300)), fill=white)
    draw.polygon(((335, 95), (435, 145), (335, 195)), fill=white)
    draw.text(
        (455, 215),
        "AERON",
        font=load_font(190, italic=True),
        anchor="lm",
        fill=white,
        stroke_width=10,
        stroke_fill=dark,
    )
    draw.line((520, 335, 1330, 335), fill=sky, width=25)
    return canvas


def render_zentra() -> Image.Image:
    canvas = Image.new("RGBA", (1150, 520), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    red: RGBA = (255, 75, 95, 255)
    white: RGBA = (255, 248, 248, 255)
    dark: RGBA = (42, 8, 14, 255)

    outline = hexagon((230, 260), 205)
    draw.line(outline[:-1], fill=red, width=34, joint="curve")
    draw.line((105, 145, 355, 145, 120, 370, 370, 370), fill=white, width=48, joint="curve")
    draw.polygon(((340, 70), (430, 105), (350, 160)), fill=red)
    draw.text(
        (475, 265),
        "ZENTRA",
        font=load_font(135),
        anchor="lm",
        fill=white,
        stroke_width=9,
        stroke_fill=dark,
    )
    return canvas


LOGO_RENDERERS: dict[str, Renderer] = {
    "veltrix": render_veltrix,
    "nordyn": render_nordyn,
    "kinetra": render_kinetra,
    "orbix": render_orbix,
    "aeron": render_aeron,
    "zentra": render_zentra,
}


def main() -> None:
    for sponsor_id, renderer in LOGO_RENDERERS.items():
        output_path = OUTPUT_DIR / f"{sponsor_id}.png"
        finalize_logo(renderer(), output_path)
        with Image.open(output_path) as logo:
            print(f"Generated {output_path}: {logo.width}x{logo.height} RGBA")


if __name__ == "__main__":
    main()

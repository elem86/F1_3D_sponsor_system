from __future__ import annotations

import io
from pathlib import Path

from panda3d.core import PNMImage, StringStream, Texture
from PIL import Image


def load_trimmed_texture(path: Path, *, pad_fraction: float = 0.06) -> tuple[Texture, float]:
    """Load a logo as a Panda3D texture cropped to its visible alpha bounds.

    Mirrors the alpha-bounds trimming already used for in-car sponsor
    placement so UI thumbnails never show a large transparent margin.
    Returns the texture and its padded width/height aspect ratio so callers
    can size a card without stretching the logo.
    """
    with Image.open(path) as source:
        rgba = source.convert("RGBA")
        bbox = rgba.getbbox()
        trimmed = rgba.crop(bbox) if bbox else rgba

    width, height = trimmed.size
    pad_x = max(1, int(width * pad_fraction))
    pad_y = max(1, int(height * pad_fraction))
    padded = Image.new("RGBA", (width + pad_x * 2, height + pad_y * 2), (0, 0, 0, 0))
    padded.paste(trimmed, (pad_x, pad_y))

    stream = io.BytesIO()
    padded.save(stream, format="PNG")

    pnm = PNMImage()
    if not pnm.read(StringStream(stream.getvalue()), "thumbnail.png"):
        raise RuntimeError(f"Could not decode trimmed logo for UI: {path}")

    texture = Texture(f"ui_logo_{path.stem}")
    texture.load(pnm)
    texture.setMinfilter(Texture.FTLinearMipmapLinear)
    texture.setMagfilter(Texture.FTLinear)
    aspect = padded.width / padded.height
    return texture, aspect

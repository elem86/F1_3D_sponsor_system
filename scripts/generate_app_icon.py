"""Generate a simple original application icon (no third-party branding).

Draws an abstract open-wheel silhouette over a small sponsor-grid mark, in
the same lime/graphite palette as the sponsor allocation UI, and saves it as
a multi-resolution .ico for use as the packaged .exe's icon.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw

BACKGROUND = (19, 20, 22, 255)
ACCENT = (184, 230, 51, 255)
ACCENT_DIM = (117, 148, 41, 255)
METAL = (86, 92, 98, 255)

OUTPUT_PNG = PROJECT_ROOT / "assets" / "branding" / "app_icon.png"
OUTPUT_ICO = PROJECT_ROOT / "assets" / "branding" / "app_icon.ico"

SIZE = 256


def draw_icon() -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), BACKGROUND)
    draw = ImageDraw.Draw(canvas)

    margin = 18
    draw.rounded_rectangle(
        (margin, margin, SIZE - margin, SIZE - margin),
        radius=28,
        outline=METAL,
        width=4,
    )

    # Small sponsor-grid mark (3 abstract slot rectangles) along the top.
    grid_top = 46
    grid_height = 28
    slot_width = 46
    slot_gap = 12
    start_x = (SIZE - (slot_width * 3 + slot_gap * 2)) // 2
    for i in range(3):
        x0 = start_x + i * (slot_width + slot_gap)
        color = ACCENT if i == 1 else ACCENT_DIM
        draw.rounded_rectangle(
            (x0, grid_top, x0 + slot_width, grid_top + grid_height),
            radius=5,
            fill=color,
        )

    # Abstract open-wheel car silhouette: a low wedge nose + two wheel discs.
    body_top = 118
    body_bottom = 176
    nose_left = 64
    nose_right = 192
    draw.polygon(
        [
            (nose_left + 26, body_top),
            (nose_right - 26, body_top),
            (nose_right, body_bottom),
            (nose_left, body_bottom),
        ],
        fill=(235, 236, 232, 255),
    )
    # Cockpit notch.
    draw.rounded_rectangle(
        (SIZE // 2 - 16, body_top - 6, SIZE // 2 + 16, body_top + 14),
        radius=6,
        fill=(235, 236, 232, 255),
    )

    wheel_radius = 26
    wheel_y = body_bottom - 6
    for cx in (nose_left + 6, nose_right - 6):
        draw.ellipse(
            (cx - wheel_radius, wheel_y - wheel_radius, cx + wheel_radius, wheel_y + wheel_radius),
            fill=(14, 15, 16, 255),
            outline=METAL,
            width=3,
        )
        draw.ellipse(
            (cx - 8, wheel_y - 8, cx + 8, wheel_y + 8),
            fill=ACCENT,
        )

    # Front wing endplate hint.
    draw.rectangle((nose_left - 10, body_bottom - 4, nose_left + 4, body_bottom + 16), fill=(235, 236, 232, 255))
    draw.rectangle((nose_right - 4, body_bottom - 4, nose_right + 10, body_bottom + 16), fill=(235, 236, 232, 255))

    return canvas


def main() -> None:
    icon = draw_icon()
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    icon.save(OUTPUT_PNG, format="PNG")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save(OUTPUT_ICO, format="ICO", sizes=sizes)
    print(f"Saved {OUTPUT_PNG}")
    print(f"Saved {OUTPUT_ICO}")


if __name__ == "__main__":
    main()

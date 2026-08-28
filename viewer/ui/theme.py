from __future__ import annotations

import os
from pathlib import Path

from panda3d.core import Filename, FontPool, TextFont


# --- Palette -----------------------------------------------------------
# Dark charcoal / graphite management-terminal palette inspired by late-90s
# / early-2000s F1 management sims. Kept centralized so no raw color tuple
# is scattered through viewer/UI code.
BACKGROUND = (0.075, 0.078, 0.086, 1.0)
PANEL_BACKGROUND = (0.106, 0.112, 0.122, 0.96)
PANEL_ALT = (0.140, 0.148, 0.160, 0.96)
PANEL_HEADER = (0.055, 0.058, 0.065, 0.98)

TEXT_PRIMARY = (0.93, 0.94, 0.92, 1.0)
TEXT_SECONDARY = (0.62, 0.65, 0.62, 1.0)
TEXT_MUTED = (0.44, 0.46, 0.45, 1.0)

ACCENT = (0.72, 0.90, 0.20, 1.0)
ACCENT_DIM = (0.46, 0.58, 0.16, 1.0)
ACCENT_TEXT = (0.10, 0.11, 0.05, 1.0)

METAL = (0.34, 0.36, 0.38, 1.0)
METAL_DARK = (0.20, 0.21, 0.23, 1.0)

BORDER = (0.30, 0.32, 0.30, 1.0)
BORDER_BRIGHT = (0.72, 0.90, 0.20, 1.0)

SELECTED = (0.72, 0.90, 0.20, 0.22)
SELECTED_BORDER = (0.72, 0.90, 0.20, 1.0)

WARNING = (0.92, 0.40, 0.32, 1.0)
SUCCESS = (0.70, 0.86, 0.45, 1.0)

TIER_COLORS = {
    "A": (0.90, 0.72, 0.24, 1.0),
    "B": (0.70, 0.78, 0.82, 1.0),
    "C": (0.62, 0.46, 0.30, 1.0),
}
TIER_COLOR_DEFAULT = TEXT_SECONDARY

# Warm, light-green tone for USD commercial-value figures, distinct from the
# lime UI accent so money reads as its own category at a glance.
VALUE_TEXT = (0.80, 0.90, 0.74, 1.0)


# --- Typography ----------------------------------------------------------
_FONT_CANDIDATES = (
    "consolab.ttf",
    "consola.ttf",
    "arialbd.ttf",
    "arial.ttf",
)

_font_cache: TextFont | None = None


def load_ui_font() -> TextFont | None:
    """Load a technical, readable system font without shipping font binaries.

    Falls back gracefully through a short candidate list and finally to
    Panda3D's built-in default font if no system font is found.
    """
    global _font_cache
    if _font_cache is not None:
        return _font_cache

    font_directory = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for candidate in _FONT_CANDIDATES:
        candidate_path = font_directory / candidate
        if not candidate_path.is_file():
            continue
        panda_filename = Filename.fromOsSpecific(str(candidate_path))
        font = FontPool.loadFont(str(panda_filename))
        if font is not None:
            _font_cache = font
            return font
    return None


# --- Spacing / sizing ------------------------------------------------------
BORDER_THICKNESS = 0.0016

TEXT_SCALE_TITLE = 0.050
TEXT_SCALE_HEADING = 0.040
TEXT_SCALE_BODY = 0.032
TEXT_SCALE_SMALL = 0.027
TEXT_SCALE_TINY = 0.023

PADDING = 0.02

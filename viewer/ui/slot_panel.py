from __future__ import annotations

import re
from typing import Any, Callable, Mapping

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from panda3d.core import NodePath, TextFont

from viewer.ui import theme


_SIDE_SUFFIXES = {
    "left": "L",
    "right": "R",
}

# Known compound tokens that must split into two display words, in the order
# they should read (e.g. "frontwing" -> "Front Wing"). Longest keys first so
# a compound match is tried before any shorter partial one.
_WORD_SPLITS = {
    "frontwing": ("Front", "Wing"),
    "rearwing": ("Rear", "Wing"),
    "sidepod": ("Sidepod",),
    "endplate": ("Endplate",),
}


def humanize_slot_name(slot_name: str) -> str:
    """Convert an internal slot id into a compact display label.

    sidepod_left -> Sidepod L
    frontwing_left_endplate -> Front Wing Endplate L
    frontwing_main -> Front Wing Main
    """
    tokens = [token for token in slot_name.split("_") if token]
    side = None
    non_side_tokens: list[str] = []
    for token in tokens:
        if token in _SIDE_SUFFIXES and side is None:
            side = _SIDE_SUFFIXES[token]
        else:
            non_side_tokens.append(token)

    words: list[str] = []
    for token in non_side_tokens:
        expansion = _WORD_SPLITS.get(token)
        if expansion is not None:
            words.extend(expansion)
        else:
            words.extend(part.capitalize() for part in re.findall(r"[a-zA-Z]+", token))

    label = " ".join(words)
    if side:
        label = f"{label} {side}"
    return label


TIER_ORDER = ("A", "B", "C")
TIER_HEADINGS = {
    "A": "A POSITIONS",
    "B": "B POSITIONS",
    "C": "C POSITIONS",
}


def group_slots_by_tier(slots: Mapping[str, Any]) -> dict[str, list[str]]:
    """Group slot ids by their configured tier, preserving declaration order."""
    grouped: dict[str, list[str]] = {tier: [] for tier in TIER_ORDER}
    other: list[str] = []
    for slot_name, slot in slots.items():
        tier = slot.get("tier") if isinstance(slot, Mapping) else None
        if tier in grouped:
            grouped[tier].append(slot_name)
        else:
            other.append(slot_name)
    if other:
        grouped["?"] = other
    return {tier: names for tier, names in grouped.items() if names}


class SlotListPanel:
    """A categorized (A/B/C) clickable list of sponsor slots."""

    def __init__(
        self,
        parent: NodePath,
        *,
        slots: Mapping[str, Any],
        on_select: Callable[[str], None],
        font: TextFont | None,
        width: float,
        top: float,
        row_height: float = 0.052,
        heading_gap: float = 0.014,
    ) -> None:
        self.root = DirectFrame(
            parent=parent,
            frameColor=(0, 0, 0, 0),
            frameSize=(0, width, -1.0, 0),
            pos=(0, 0, top),
        )
        self._font = font
        self._on_select = on_select
        self._row_height = row_height
        self._width = width
        self._buttons: dict[str, DirectButton] = {}
        self._selected: str | None = None

        grouped = group_slots_by_tier(slots)
        cursor = 0.0
        for tier in list(TIER_ORDER) + ["?"]:
            names = grouped.get(tier)
            if not names:
                continue
            heading_text = TIER_HEADINGS.get(tier, "OTHER POSITIONS")
            DirectLabel(
                parent=self.root,
                text=heading_text,
                text_align=-1,
                text_scale=theme.TEXT_SCALE_TINY,
                text_fg=theme.TIER_COLORS.get(tier, theme.TIER_COLOR_DEFAULT),
                text_font=font,
                frameColor=(0, 0, 0, 0),
                pos=(0.006, 0, cursor - theme.TEXT_SCALE_TINY),
            )
            cursor -= theme.TEXT_SCALE_TINY + heading_gap
            for slot_name in names:
                self._make_row(slot_name, cursor)
                cursor -= row_height
            cursor -= heading_gap

        self.total_height = -cursor

    def _make_row(self, slot_name: str, y: float) -> None:
        label_text = humanize_slot_name(slot_name)
        button = DirectButton(
            parent=self.root,
            relief=DGG.FLAT,
            frameColor=theme.PANEL_ALT,
            frameSize=(0, self._width, -self._row_height + 0.006, 0.006),
            pos=(0, 0, y),
            text=label_text,
            text_align=-1,
            text_scale=theme.TEXT_SCALE_SMALL,
            text_fg=theme.TEXT_PRIMARY,
            text_font=self._font,
            text_pos=(0.014, -self._row_height * 0.62),
            command=self._handle_click,
            extraArgs=[slot_name],
        )
        button.bind("enter", lambda _e, n=slot_name: self._set_hover(n, True))
        button.bind("exit", lambda _e, n=slot_name: self._set_hover(n, False))
        self._buttons[slot_name] = button

    def _handle_click(self, slot_name: str) -> None:
        self._on_select(slot_name)

    def _set_hover(self, slot_name: str, hovered: bool) -> None:
        if slot_name == self._selected:
            return
        button = self._buttons.get(slot_name)
        if button is not None:
            button["frameColor"] = theme.PANEL_HEADER if hovered else theme.PANEL_ALT

    def set_selected(self, slot_name: str | None) -> None:
        if self._selected is not None:
            previous = self._buttons.get(self._selected)
            if previous is not None:
                previous["frameColor"] = theme.PANEL_ALT
                previous["text_fg"] = theme.TEXT_PRIMARY
        self._selected = slot_name
        if slot_name is not None:
            current = self._buttons.get(slot_name)
            if current is not None:
                current["frameColor"] = theme.SELECTED
                current["text_fg"] = theme.ACCENT

    def destroy(self) -> None:
        self.root.destroy()

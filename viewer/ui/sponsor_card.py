from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from panda3d.core import CardMaker, NodePath, TextFont, TransparencyAttrib

from livery.sponsor_values import format_usd_millions
from viewer.ui import theme

# Temporary diagnostic logging for the sponsor-card selection bug fix; kept
# behind a flag rather than removed outright per the debugging instructions.
DEBUG_UI = False


@dataclass(frozen=True)
class SponsorCardGeometry:
    """Pixel-independent layout for one sponsor card, in aspect2d units."""

    width: float
    height: float


class SponsorCard:
    """One clickable sponsor entry: logo thumbnail + name, with a select border."""

    def __init__(
        self,
        parent: NodePath,
        *,
        sponsor_id: str,
        name: str,
        texture,
        texture_aspect: float,
        geometry: SponsorCardGeometry,
        pos: tuple[float, float],
        on_click: Callable[[str], None],
        font: TextFont | None,
        contract_value_usd: int | None = None,
    ) -> None:
        self.sponsor_id = sponsor_id
        self._on_click = on_click
        width, height = geometry.width, geometry.height

        self.frame = DirectFrame(
            parent=parent,
            frameColor=theme.PANEL_ALT,
            frameSize=(0, width, -height, 0),
            pos=(pos[0], 0, pos[1]),
        )
        self.border = DirectFrame(
            parent=self.frame,
            frameColor=(0, 0, 0, 0),
            frameSize=(0, width, -height, 0),
            pos=(0, 0, 0),
        )
        self._set_border_color(theme.BORDER)

        logo_area_height = height * 0.62
        logo_max_width = width * 0.8
        logo_max_height = logo_area_height * 0.86
        logo_width = logo_max_width
        logo_height = logo_width / texture_aspect
        if logo_height > logo_max_height:
            logo_height = logo_max_height
            logo_width = logo_height * texture_aspect

        card_maker = CardMaker(f"sponsor_logo_{sponsor_id}")
        card_maker.setFrame(-logo_width / 2, logo_width / 2, -logo_height / 2, logo_height / 2)
        logo_node = NodePath(card_maker.generate())
        logo_node.reparentTo(self.frame)
        logo_node.setTexture(texture)
        logo_node.setTransparency(TransparencyAttrib.M_alpha)
        logo_node.setPos(width / 2, 0, -logo_area_height / 2)

        # Small requirement-status dot in the top-left corner: gray = not on
        # the car, amber = assigned but under its required exposure, green =
        # requirement met. Purely informational -- never blocks placement.
        dot_size = min(width, height) * 0.09
        dot_margin = dot_size * 0.9
        card_maker_dot = CardMaker(f"sponsor_status_dot_{sponsor_id}")
        card_maker_dot.setFrame(-dot_size / 2, dot_size / 2, -dot_size / 2, dot_size / 2)
        self.status_dot = NodePath(card_maker_dot.generate())
        self.status_dot.reparentTo(self.frame)
        self.status_dot.setPos(dot_margin, 0, -dot_margin)
        self.status_dot.setColor(theme.EXPOSURE_INACTIVE)

        name_row_y = -height + height * 0.16
        self.name_label = DirectLabel(
            parent=self.frame,
            text=name.upper(),
            text_align=-1,
            text_scale=theme.TEXT_SCALE_SMALL,
            text_fg=theme.TEXT_PRIMARY,
            text_font=font,
            frameColor=(0, 0, 0, 0),
            pos=(width * 0.08, 0, name_row_y),
        )
        self.value_label = None
        if contract_value_usd is not None:
            self.value_label = DirectLabel(
                parent=self.frame,
                text=format_usd_millions(contract_value_usd),
                text_align=1,
                text_scale=theme.TEXT_SCALE_SMALL,
                text_fg=theme.VALUE_TEXT,
                text_font=font,
                frameColor=(0, 0, 0, 0),
                pos=(width * 0.92, 0, name_row_y),
            )

        # relief=None leaves the underlying PGItem without a computed frame
        # style; in this Panda3D build that meant the button's mouse region
        # was never registered with the MouseWatcher unless some other
        # relief'd sibling widget happened to force a frame-style recompute
        # first. relief=DGG.FLAT (transparent) gives the button a real frame
        # style so its whole area is reliably clickable, while staying
        # visually identical since self.frame already paints the background.
        self.button = DirectButton(
            parent=self.frame,
            relief=DGG.FLAT,
            frameColor=(0, 0, 0, 0),
            frameSize=(0, width, -height, 0),
            pos=(0, 0, 0),
            command=self._handle_click,
        )
        self.button.bind("enter", lambda _event: self._set_hover(True))
        self.button.bind("exit", lambda _event: self._set_hover(False))
        self._selected = False
        self._hovered = False

    def _handle_click(self) -> None:
        if DEBUG_UI:
            print(f"Sponsor clicked: {self.sponsor_id}")
        self._on_click(self.sponsor_id)

    def _set_hover(self, hovered: bool) -> None:
        self._hovered = hovered
        if not self._selected:
            self.frame["frameColor"] = (
                theme.PANEL_HEADER if hovered else theme.PANEL_ALT
            )

    def _set_border_color(self, color: tuple[float, float, float, float]) -> None:
        thickness = theme.BORDER_THICKNESS * 4
        width = self.frame["frameSize"][1]
        height = -self.frame["frameSize"][2]
        for child in self.border.getChildren():
            child.removeNode()
        for frame_spec in (
            (0, width, 0, thickness),
            (0, width, -height, -height + thickness),
            (0, thickness, -height, 0),
            (width - thickness, width, -height, 0),
        ):
            DirectFrame(
                parent=self.border,
                frameColor=color,
                frameSize=frame_spec,
                pos=(0, 0, 0),
            )

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        if selected:
            self.frame["frameColor"] = theme.SELECTED
            self._set_border_color(theme.SELECTED_BORDER)
        else:
            self.frame["frameColor"] = theme.PANEL_ALT
            self._set_border_color(theme.BORDER)

    def set_exposure_status(self, *, active: bool, requirement_met: bool) -> None:
        """Recolor the status dot: gray/amber/green, per exposure state."""
        if not active:
            color = theme.EXPOSURE_INACTIVE
        elif requirement_met:
            color = theme.EXPOSURE_MET
        else:
            color = theme.EXPOSURE_UNDER
        self.status_dot.setColor(color)

    def destroy(self) -> None:
        self.frame.destroy()

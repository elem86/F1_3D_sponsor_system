from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.gui.DirectScrolledFrame import DirectScrolledFrame
from panda3d.core import NodePath

from livery.sponsor_values import format_usd
from viewer.ui import theme
from viewer.ui.slot_panel import SlotListPanel, humanize_slot_name
from viewer.ui.sponsor_card import SponsorCard, SponsorCardGeometry
from viewer.ui.texture_utils import load_trimmed_texture


class SponsorAllocationUI:
    """Owns every on-screen widget for the one-screen sponsor allocation UI.

    This class is presentation-only: it reads slot/sponsor/assignment state
    handed to it by CarViewer and calls back into CarViewer for every
    state-changing action (select slot, select sponsor, apply, remove,
    save). It never touches livery generation or the 3D scene itself.
    """

    # Fraction of the aspect2d width given to the 3D viewport (left side).
    VIEWPORT_FRACTION = 0.66

    def __init__(
        self,
        base,
        *,
        team_name: str,
        driver_number: str,
        slots: Mapping[str, Any],
        sponsors: Mapping[str, Any],
        assignments: Mapping[str, str],
        tier_values: Mapping[str, int],
        on_select_slot: Callable[[str], None],
        on_select_sponsor: Callable[[str], None],
        on_apply: Callable[[], None],
        on_remove: Callable[[], None],
        on_save: Callable[[], None],
    ) -> None:
        self.base = base
        self.team_name = team_name
        self.driver_number = driver_number
        self.slots = slots
        self.sponsors = sponsors
        self.assignments = assignments
        self.tier_values = tier_values
        self._on_select_slot = on_select_slot
        self._on_select_sponsor = on_select_sponsor
        self._on_apply = on_apply
        self._on_remove = on_remove
        self._on_save = on_save

        self.font = theme.load_ui_font()
        self._sponsor_cards: dict[str, SponsorCard] = {}
        self._sponsor_textures: dict[str, tuple[Any, float]] = {}
        self._slot_list: SlotListPanel | None = None
        self._root_nodes: list[NodePath] = []

        self._build()
        self.base.accept("aspectRatioChanged", self._on_resize)

    # -- Layout -------------------------------------------------------

    def _on_resize(self) -> None:
        self._teardown()
        self._build()

    def _teardown(self) -> None:
        for node in self._root_nodes:
            node.destroy()
        self._root_nodes.clear()
        self._sponsor_cards.clear()
        self._slot_list = None

    def _build(self) -> None:
        aspect = self.base.getAspectRatio()
        self.left = -aspect
        self.right = aspect
        self.top = 1.0
        self.bottom = -1.0

        header_height = 0.11
        bottom_bar_height = 0.40
        margin = 0.018

        self._build_header(header_height)
        self._build_side_panel(header_height, bottom_bar_height, margin, aspect)
        self._build_bottom_bar(bottom_bar_height, margin, aspect)
        self._build_viewport_hint(header_height, bottom_bar_height, aspect)

    # -- Header ---------------------------------------------------------

    def _build_header(self, height: float) -> None:
        header = DirectFrame(
            parent=self.base.aspect2d,
            frameColor=theme.PANEL_HEADER,
            frameSize=(self.left, self.right, self.top - height, self.top),
            pos=(0, 0, 0),
        )
        self._root_nodes.append(header)

        DirectLabel(
            parent=header,
            text=f"{self.team_name.upper()} MOTORSPORT",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_TITLE,
            text_fg=theme.ACCENT,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(self.left + 0.03, 0, self.top - height * 0.62),
        )
        DirectLabel(
            parent=header,
            text="SPONSOR ALLOCATION",
            text_align=0,
            text_scale=theme.TEXT_SCALE_HEADING,
            text_fg=theme.TEXT_PRIMARY,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, self.top - height * 0.62),
        )
        DirectLabel(
            parent=header,
            text=f"DRIVER #{self.driver_number}",
            text_align=1,
            text_scale=theme.TEXT_SCALE_BODY,
            text_fg=theme.TEXT_SECONDARY,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(self.right - 0.03, 0, self.top - height * 0.62),
        )
        # Thin accent underline gives the header a technical-terminal edge.
        underline = DirectFrame(
            parent=header,
            frameColor=theme.ACCENT_DIM,
            frameSize=(self.left, self.right, -0.004, 0.0),
            pos=(0, 0, self.top - height),
        )
        self._root_nodes.append(underline)

    # -- Right-hand side panel (sponsor list) ----------------------------

    def _build_side_panel(
        self, header_height: float, bottom_bar_height: float, margin: float, aspect: float
    ) -> None:
        panel_left = self.left + (self.right - self.left) * self.VIEWPORT_FRACTION
        panel_top = self.top - header_height
        panel_bottom = self.bottom + bottom_bar_height

        panel = DirectFrame(
            parent=self.base.aspect2d,
            frameColor=theme.PANEL_BACKGROUND,
            frameSize=(panel_left, self.right, panel_bottom, panel_top),
            pos=(0, 0, 0),
        )
        self._root_nodes.append(panel)

        DirectLabel(
            parent=panel,
            text="AVAILABLE SPONSORS",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_HEADING,
            text_fg=theme.TEXT_PRIMARY,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(panel_left + 0.025, 0, panel_top - 0.055),
        )

        list_top = panel_top - 0.10
        list_bottom = panel_bottom + margin
        list_width = (self.right - margin) - (panel_left + margin)

        canvas_width = list_width - 0.06
        card_width = canvas_width
        card_height = 0.16
        card_gap = 0.018
        canvas_height = len(self.sponsors) * (card_height + card_gap)

        self.sponsor_scroll = DirectScrolledFrame(
            parent=panel,
            frameColor=(0, 0, 0, 0),
            frameSize=(panel_left + margin, self.right - margin, list_bottom, list_top),
            canvasSize=(0, canvas_width, -max(canvas_height, list_top - list_bottom), 0),
            scrollBarWidth=0.024,
            verticalScroll_relief="flat",
            verticalScroll_frameColor=theme.PANEL_ALT,
            verticalScroll_thumb_relief="flat",
            verticalScroll_thumb_frameColor=theme.ACCENT_DIM,
            horizontalScroll_relief="flat",
            manageScrollBars=True,
        )
        self.sponsor_scroll.setPos(0, 0, 0)
        self._root_nodes.append(self.sponsor_scroll)
        canvas = self.sponsor_scroll.getCanvas()

        cursor_y = 0.0
        self._sponsor_cards.clear()
        for sponsor_id, data in self.sponsors.items():
            name = data.get("name", sponsor_id)
            texture, texture_aspect = self._get_sponsor_texture(sponsor_id, data)
            card = SponsorCard(
                canvas,
                sponsor_id=sponsor_id,
                name=name,
                texture=texture,
                texture_aspect=texture_aspect,
                geometry=SponsorCardGeometry(width=card_width, height=card_height),
                pos=(0.0, cursor_y),
                on_click=self._on_select_sponsor,
                font=self.font,
            )
            self._sponsor_cards[sponsor_id] = card
            cursor_y -= card_height + card_gap

    def _get_sponsor_texture(self, sponsor_id: str, data: Mapping[str, Any]):
        cached = self._sponsor_textures.get(sponsor_id)
        if cached is not None:
            return cached
        logo_path = Path(data["logo"])
        texture, aspect = load_trimmed_texture(logo_path)
        self._sponsor_textures[sponsor_id] = (texture, aspect)
        return texture, aspect

    # -- Bottom bar: slot list + slot info + assignment + actions --------

    def _build_bottom_bar(self, height: float, margin: float, aspect: float) -> None:
        bar = DirectFrame(
            parent=self.base.aspect2d,
            frameColor=theme.PANEL_BACKGROUND,
            frameSize=(self.left, self.right, self.bottom, self.bottom + height),
            pos=(0, 0, 0),
        )
        self._root_nodes.append(bar)
        top = self.bottom + height

        divider_x = self.left + (self.right - self.left) * 0.36
        info_x = divider_x + (self.right - divider_x) * 0.5

        # -- Left column: categorized slot list -------------------------
        slot_panel_frame = DirectFrame(
            parent=bar,
            frameColor=(0, 0, 0, 0),
            frameSize=(self.left, divider_x, self.bottom, top),
            pos=(0, 0, 0),
        )
        DirectLabel(
            parent=slot_panel_frame,
            text="SPONSOR POSITIONS",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_TINY,
            text_fg=theme.TEXT_SECONDARY,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(self.left + margin, 0, top - 0.03),
        )
        self.value_summary_label = DirectLabel(
            parent=slot_panel_frame,
            text="ASSIGNED -- / --",
            text_align=1,
            text_scale=theme.TEXT_SCALE_TINY,
            text_fg=theme.VALUE_TEXT,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(divider_x - margin, 0, top - 0.03),
        )
        list_area_top = top - 0.06
        list_area_bottom = self.bottom + margin
        scroll_bar_width = 0.02
        list_width = divider_x - self.left - margin * 2 - scroll_bar_width

        canvas_height = 0.0
        if self.slots:
            # Rough estimate; SlotListPanel reports the real height after build.
            canvas_height = len(self.slots) * 0.052 + 3 * 0.05

        self.slot_scroll = DirectScrolledFrame(
            parent=slot_panel_frame,
            frameColor=(0, 0, 0, 0),
            frameSize=(self.left + margin, divider_x - margin, list_area_bottom, list_area_top),
            canvasSize=(0, list_width, -max(canvas_height, list_area_top - list_area_bottom), 0),
            scrollBarWidth=scroll_bar_width,
            verticalScroll_relief="flat",
            verticalScroll_frameColor=theme.PANEL_ALT,
            verticalScroll_thumb_relief="flat",
            verticalScroll_thumb_frameColor=theme.ACCENT_DIM,
            horizontalScroll_relief="flat",
            manageScrollBars=True,
        )
        self._root_nodes.append(self.slot_scroll)

        self._slot_list = SlotListPanel(
            self.slot_scroll.getCanvas(),
            slots=self.slots,
            tier_values=self.tier_values,
            assignments=self.assignments,
            sponsors=self.sponsors,
            on_select=self._on_select_slot,
            font=self.font,
            width=list_width,
            top=0.0,
        )

        # -- Middle column: selected position + assignment info ---------
        info_frame = DirectFrame(
            parent=bar,
            frameColor=(0, 0, 0, 0),
            frameSize=(divider_x, self.right, self.bottom, top),
            pos=(0, 0, 0),
        )
        vertical_divider = DirectFrame(
            parent=bar,
            frameColor=theme.BORDER,
            frameSize=(-0.0012, 0.0012, self.bottom + margin * 0.5, top - margin * 0.5),
            pos=(divider_x, 0, 0),
        )
        self._root_nodes.append(vertical_divider)

        column_width = (self.right - divider_x) / 2 - margin

        # SELECTED POSITION column
        selected_left = divider_x + margin
        DirectLabel(
            parent=info_frame,
            text="SELECTED POSITION",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_TINY,
            text_fg=theme.TEXT_SECONDARY,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(selected_left, 0, top - 0.03),
        )
        self.slot_name_label = DirectLabel(
            parent=info_frame,
            text="--",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_HEADING,
            text_fg=theme.TEXT_PRIMARY,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(selected_left, 0, top - 0.075),
        )
        DirectLabel(
            parent=info_frame,
            text="CLASS",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_TINY,
            text_fg=theme.TEXT_MUTED,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(selected_left, 0, top - 0.115),
        )
        self.slot_tier_label = DirectLabel(
            parent=info_frame,
            text="--",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_BODY,
            text_fg=theme.TIER_COLOR_DEFAULT,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(selected_left, 0, top - 0.150),
        )
        DirectLabel(
            parent=info_frame,
            text="VALUE",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_TINY,
            text_fg=theme.TEXT_MUTED,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(selected_left, 0, top - 0.190),
        )
        self.slot_value_label = DirectLabel(
            parent=info_frame,
            text="--",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_BODY,
            text_fg=theme.VALUE_TEXT,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(selected_left, 0, top - 0.225),
        )

        # CURRENT ASSIGNMENT column
        assignment_left = divider_x + column_width + margin * 2
        DirectLabel(
            parent=info_frame,
            text="CURRENT SPONSOR",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_TINY,
            text_fg=theme.TEXT_SECONDARY,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(assignment_left, 0, top - 0.03),
        )
        self.assignment_label = DirectLabel(
            parent=info_frame,
            text="EMPTY",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_HEADING,
            text_fg=theme.TEXT_MUTED,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(assignment_left, 0, top - 0.075),
        )
        DirectLabel(
            parent=info_frame,
            text="SELECTED SPONSOR",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_TINY,
            text_fg=theme.TEXT_MUTED,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(assignment_left, 0, top - 0.115),
        )
        self.pending_sponsor_label = DirectLabel(
            parent=info_frame,
            text="--",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_BODY,
            text_fg=theme.ACCENT,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(assignment_left, 0, top - 0.150),
        )
        DirectLabel(
            parent=info_frame,
            text="ALLOCATED VALUE",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_TINY,
            text_fg=theme.TEXT_MUTED,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(assignment_left, 0, top - 0.190),
        )
        self.sponsor_value_label = DirectLabel(
            parent=info_frame,
            text="--",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_BODY,
            text_fg=theme.VALUE_TEXT,
            text_font=self.font,
            frameColor=(0, 0, 0, 0),
            pos=(assignment_left, 0, top - 0.225),
        )

        # -- Action buttons and status line ------------------------------
        # Buttons anchor from the bottom edge upward so nothing overflows
        # the bar regardless of window aspect ratio.
        button_height = 0.05
        button_bottom_margin = 0.024
        button_top_y = self.bottom + button_bottom_margin + button_height

        remove_width = column_width * 0.42
        remove_button = self._make_button(
            info_frame,
            text="REMOVE",
            pos=(assignment_left, button_top_y),
            width=remove_width,
            height=button_height,
            primary=False,
            command=self._on_remove,
        )
        self._root_nodes_extend(remove_button)

        save_width = column_width * 0.9
        save_button = self._make_button(
            info_frame,
            text="SAVE LAYOUT",
            pos=(assignment_left + remove_width + margin, button_top_y),
            width=column_width - remove_width - margin,
            height=button_height,
            primary=False,
            command=self._on_save,
            accent_border=True,
        )
        self._root_nodes_extend(save_button)

        apply_width = divider_x - self.left - margin * 2
        apply_button = self._make_button(
            slot_panel_frame,
            text="APPLY SPONSOR",
            pos=(self.left + margin, button_top_y),
            width=apply_width,
            height=button_height,
            primary=True,
            command=self._on_apply,
        )
        self._root_nodes_extend(apply_button)

        status_y = button_top_y + button_height + 0.014
        self.status_label = DirectLabel(
            parent=info_frame,
            text="Ready",
            text_align=-1,
            text_scale=theme.TEXT_SCALE_SMALL,
            text_fg=theme.SUCCESS,
            text_font=self.font,
            text_wordwrap=26,
            frameColor=(0, 0, 0, 0),
            pos=(selected_left, 0, status_y),
        )

    def _root_nodes_extend(self, node: NodePath) -> None:
        self._root_nodes.append(node)

    def _make_button(
        self,
        parent: NodePath,
        *,
        text: str,
        pos: tuple[float, float],
        width: float,
        height: float,
        primary: bool,
        command: Callable[[], None],
        accent_border: bool = False,
    ) -> NodePath:
        color = theme.ACCENT if primary else theme.PANEL_ALT
        text_color = theme.ACCENT_TEXT if primary else theme.TEXT_PRIMARY
        border_color = theme.ACCENT if (primary or accent_border) else theme.BORDER

        wrapper = NodePath("button_wrapper")
        wrapper.reparentTo(parent)
        wrapper.setPos(pos[0], 0, pos[1])

        DirectFrame(
            parent=wrapper,
            frameColor=border_color,
            frameSize=(-theme.BORDER_THICKNESS * 3, width + theme.BORDER_THICKNESS * 3,
                       -height - theme.BORDER_THICKNESS * 3, theme.BORDER_THICKNESS * 3),
            pos=(0, 0, 0),
        )
        button = DirectButton(
            parent=wrapper,
            relief=1,
            frameColor=color,
            frameSize=(0, width, -height, 0),
            text=text,
            text_align=0,
            text_scale=theme.TEXT_SCALE_BODY,
            text_fg=text_color,
            text_font=self.font,
            text_pos=(width / 2, -height * 0.65),
            pos=(0, 0, 0),
            command=command,
        )
        return wrapper

    # -- Viewport helper text --------------------------------------------

    def _build_viewport_hint(
        self, header_height: float, bottom_bar_height: float, aspect: float
    ) -> None:
        panel_left = self.left + (self.right - self.left) * self.VIEWPORT_FRACTION
        hint = DirectLabel(
            parent=self.base.aspect2d,
            text="DRAG: ROTATE   WHEEL: ZOOM   R: RESET",
            text_align=0,
            text_scale=theme.TEXT_SCALE_SMALL,
            text_fg=theme.TEXT_SECONDARY,
            text_font=self.font,
            frameColor=theme.PANEL_HEADER,
            pos=((self.left + panel_left) / 2, 0, self.bottom + bottom_bar_height + 0.045),
        )
        self._root_nodes.append(hint)

    # -- Public update API used by CarViewer ------------------------------

    def viewport_bounds(self) -> tuple[float, float, float, float]:
        """Return (left, right, bottom, top) of the 3D viewport in aspect2d units."""
        panel_left = self.left + (self.right - self.left) * self.VIEWPORT_FRACTION
        return self.left, panel_left, self.bottom + 0.34, self.top - 0.11

    def set_selected_slot(
        self, slot_name: str | None, tier: str | None, value: int | None = None
    ) -> None:
        if self._slot_list is not None:
            self._slot_list.set_selected(slot_name)
        label = humanize_slot_name(slot_name) if slot_name else "--"
        self.slot_name_label["text"] = label
        self.slot_tier_label["text"] = tier or "--"
        self.slot_tier_label["text_fg"] = theme.TIER_COLORS.get(tier, theme.TIER_COLOR_DEFAULT)
        self.slot_value_label["text"] = format_usd(value) if value is not None else "--"

    def set_current_assignment(self, sponsor_name: str | None) -> None:
        if sponsor_name:
            self.assignment_label["text"] = sponsor_name.upper()
            self.assignment_label["text_fg"] = theme.TEXT_PRIMARY
        else:
            self.assignment_label["text"] = "EMPTY"
            self.assignment_label["text_fg"] = theme.TEXT_MUTED

    def set_selected_sponsor(self, sponsor_id: str | None) -> None:
        for sid, card in self._sponsor_cards.items():
            card.set_selected(sid == sponsor_id)
        if sponsor_id is not None:
            name = self.sponsors.get(sponsor_id, {}).get("name", sponsor_id)
            self.pending_sponsor_label["text"] = name.upper()
        else:
            self.pending_sponsor_label["text"] = "--"

    def set_sponsor_allocated_value(self, sponsor_id: str | None, value: int | None) -> None:
        if sponsor_id is None or value is None:
            self.sponsor_value_label["text"] = "--"
        else:
            self.sponsor_value_label["text"] = format_usd(value)

    def set_value_summary(self, assigned: int, total: int) -> None:
        self.value_summary_label["text"] = (
            f"ASSIGNED {format_usd(assigned)} / {format_usd(total)}"
        )

    def set_slot_occupants(
        self, assignments: Mapping[str, str], sponsors: Mapping[str, Any]
    ) -> None:
        if self._slot_list is not None:
            self._slot_list.set_occupants(assignments, sponsors)

    def set_status(self, message: str, *, error: bool = False) -> None:
        self.status_label["text"] = message
        self.status_label["text_fg"] = theme.WARNING if error else theme.SUCCESS

    def destroy(self) -> None:
        self.base.ignore("aspectRatioChanged")
        self._teardown()

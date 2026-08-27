from __future__ import annotations

import json
import math
import struct
from pathlib import Path
from typing import Any

from direct.gui.DirectGui import (
    DirectButton,
    DirectFrame,
    DirectLabel,
    DirectOptionMenu,
)
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Filename,
    Point3,
    Texture,
    TextureStage,
    WindowProperties,
)

from livery.base_generator import generate_team_base
from livery.config_loader import load_json
from livery.generator import LiveryGenerator


class ViewerConfigError(ValueError):
    """Raised when runtime livery configuration is incomplete or inconsistent."""


class CarViewer(ShowBase):
    """Interactive Panda3D car viewer and sponsor assignment editor."""

    def __init__(self, project_root: str | Path | None = None):
        # Resolve every runtime asset from the repository, not the launch directory.
        self.project_root = Path(project_root or Path(__file__).resolve().parents[1])
        self.project_root = self.project_root.resolve()  # Normalize the asset root.

        # These are the existing production inputs used by the offline generator.
        self.slots_path = self.project_root / "config" / "sponsor_slots.json"  # Calibrated slots.
        self.sponsors_path = self.project_root / "config" / "sponsors.json"  # Logo catalog.
        self.assignments_path = self.project_root / "config" / "demo_assignments.json"  # UI state.
        self.team_path = self.project_root / "config" / "demo_team.json"  # Base color source.
        self.base_texture_path = self.project_root / "generated" / "demo_team_base.png"
        self.livery_texture_path = (
            self.project_root / "generated" / "demo_team_livery_runtime.png"
        )

        # Load and validate configuration before opening a graphics window so that
        # malformed files produce a focused startup error.
        self.slots = self._load_mapping(self.slots_path, "sponsor slots")
        self.sponsors = self._load_mapping(self.sponsors_path, "sponsors")
        self.assignments = self._load_mapping(self.assignments_path, "assignments")
        self.team = self._load_mapping(self.team_path, "team")
        self.model_path = self._resolve_model_path()
        self._validate_config()
        self.generator_sponsors = self._absolute_sponsor_paths()  # CWD-safe logo paths.

        super().__init__()

        # Scene and interaction state is kept on the viewer instance so callbacks
        # can update only the selected assignment and current texture.
        self.car_model = None
        self.livery_nodes = []  # Body and wing nodes receiving the live texture.
        self.wheel_nodes = []  # Wheel nodes that must retain black materials.
        self.current_texture: Texture | None = None
        self.texture_revision = 0  # Gives every reload a unique texture object.
        self.orbiting = False  # True only while the left mouse button is held.
        self.last_mouse = None  # Previous normalized pointer coordinates.
        self.orbit_target = Point3(0, 0, 0)  # Updated from the complete car bounds.
        self.default_yaw = -28.0
        self.default_pitch = 18.0
        self.default_distance = 11.0
        self.yaw = self.default_yaw  # Horizontal angle around world Z.
        self.pitch = self.default_pitch  # Vertical angle, clamped to avoid flips.
        self.distance = self.default_distance  # Distance from the car center.
        self.minimum_distance = 5.0
        self.maximum_distance = 24.0
        self.selected_slot = next(iter(self.slots))  # First configured slot.
        self.selected_sponsor = next(iter(self.sponsors))  # First catalog entry.

        self._setup_window()
        self._setup_lights()
        self._load_car()
        self._setup_camera()
        self._setup_ui()
        self._setup_controls()

        try:
            self.refresh_livery()
        except Exception as error:
            self.destroy()
            raise RuntimeError(f"Initial livery generation failed: {error}") from error

        print(f"[INFO] GLB loaded: {self.model_path}")
        print(f"[INFO] Sponsor count: {len(self.sponsors)}")
        print(f"[INFO] Slot count: {len(self.slots)}")
        print(f"[INFO] Current assignment count: {len(self.assignments)}")
        print(f"[INFO] Livery texture path: {self.livery_texture_path}")

    @staticmethod
    def _load_mapping(path: Path, description: str) -> dict[str, Any]:
        try:
            data = load_json(path)
        except json.JSONDecodeError as error:
            raise ViewerConfigError(
                f"Malformed {description} JSON at {path}: "
                f"line {error.lineno}, column {error.colno}: {error.msg}"
            ) from error
        except OSError as error:
            raise ViewerConfigError(f"Could not load {description} from {path}: {error}") from error

        if not isinstance(data, dict):
            raise ViewerConfigError(f"{description.capitalize()} config must be a JSON object: {path}")
        return data

    def _resolve_model_path(self) -> Path:
        # Prefer the production asset. The fallback keeps older working copies of
        # the repository runnable while making the mismatch visible at startup.
        requested = self.project_root / "assets" / "models" / "f1_car.glb"
        if requested.is_file():
            return requested

        development_fallback = (
            self.project_root / "assets" / "models" / "f1_car_test.glb"
        )
        if development_fallback.is_file():
            print(
                f"[WARNING] Requested GLB is missing: {requested}\n"
                f"[WARNING] Using verified development model: {development_fallback}"
            )
            return development_fallback

        raise FileNotFoundError(
            "F1 car GLB is missing. Expected "
            f"{requested} (development fallback also missing: {development_fallback})"
        )

    def _validate_config(self) -> None:
        if not self.slots:
            raise ViewerConfigError(f"No sponsor slots are defined in {self.slots_path}")
        if not self.sponsors:
            raise ViewerConfigError(f"No sponsors are defined in {self.sponsors_path}")

        for slot_name, slot in self.slots.items():
            if not isinstance(slot, dict):
                raise ViewerConfigError(f"Slot {slot_name!r} must be a JSON object")
            if not isinstance(slot.get("object"), str) or not slot["object"]:
                raise ViewerConfigError(
                    f"Slot {slot_name!r} must define a non-empty object name"
                )

        missing_logos = []
        for sponsor_id, sponsor in self.sponsors.items():
            if not isinstance(sponsor, dict):
                raise ViewerConfigError(f"Sponsor {sponsor_id!r} must be a JSON object")
            logo = sponsor.get("logo")
            if not isinstance(logo, str) or not logo:
                raise ViewerConfigError(f"Sponsor {sponsor_id!r} has no logo path")
            logo_path = Path(logo)
            if not logo_path.is_absolute():
                logo_path = self.project_root / logo_path
            if not logo_path.is_file():
                missing_logos.append(f"{sponsor_id}: {logo_path}")

        if missing_logos:
            raise FileNotFoundError(
                "Sponsor logo file(s) missing:\n  " + "\n  ".join(missing_logos)
            )

        for slot_name, sponsor_id in self.assignments.items():
            if not isinstance(slot_name, str) or not isinstance(sponsor_id, str):
                raise ViewerConfigError(
                    "Every assignment must map a string slot name to a string sponsor id"
                )

        unknown_slots = sorted(set(self.assignments) - set(self.slots))
        unknown_sponsors = sorted(set(self.assignments.values()) - set(self.sponsors))
        if unknown_slots:
            raise ViewerConfigError(
                f"Assignments reference unknown slot(s): {', '.join(unknown_slots)}"
            )
        if unknown_sponsors:
            raise ViewerConfigError(
                f"Assignments reference unknown sponsor(s): {', '.join(unknown_sponsors)}"
            )

        colors = self.team.get("colors")
        if not isinstance(colors, dict) or "primary" not in colors:
            raise ViewerConfigError(
                f"Team config must define colors.primary: {self.team_path}"
            )

    def _absolute_sponsor_paths(self) -> dict[str, Any]:
        # The livery generator accepts paths directly; absolute paths also allow
        # the viewer to be launched from outside the repository directory.
        resolved = {}
        for sponsor_id, sponsor in self.sponsors.items():
            entry = dict(sponsor)
            logo_path = Path(entry["logo"])
            if not logo_path.is_absolute():
                logo_path = self.project_root / logo_path
            entry["logo"] = str(logo_path.resolve())
            resolved[sponsor_id] = entry
        return resolved

    def _setup_window(self) -> None:
        self.disableMouse()  # Replace Panda3D's default camera controller.
        self.setBackgroundColor(0.12, 0.14, 0.17, 1.0)  # Neutral backdrop.
        if self.win is not None and hasattr(self.win, "requestProperties"):
            properties = WindowProperties()
            properties.setTitle("F1 Sponsor Editor")
            self.win.requestProperties(properties)
        if self.camLens is not None:
            self.camLens.setFov(45)
            self.camLens.setNearFar(0.05, 250.0)

    def _setup_lights(self) -> None:
        ambient = AmbientLight("ambient")
        ambient.setColor((0.34, 0.36, 0.40, 1.0))
        self.render.setLight(self.render.attachNewNode(ambient))

        key = DirectionalLight("key")
        key.setColor((1.0, 0.97, 0.92, 1.0))
        key_node = self.render.attachNewNode(key)
        key_node.setHpr(-35, -48, 0)
        self.render.setLight(key_node)

        fill = DirectionalLight("fill")
        fill.setColor((0.45, 0.52, 0.65, 1.0))
        fill_node = self.render.attachNewNode(fill)
        fill_node.setHpr(145, -22, 0)
        self.render.setLight(fill_node)

    def _load_car(self) -> None:
        # Panda3D supplies GLB loading through the normal model loader.
        panda_path = Filename.fromOsSpecific(str(self.model_path))
        try:
            model = self.loader.loadModel(panda_path)
        except Exception as error:
            raise RuntimeError(f"Panda3D could not load GLB {self.model_path}: {error}") from error
        if model is None or model.isEmpty():
            raise RuntimeError(f"Panda3D returned an empty model for {self.model_path}")

        self.car_model = model
        self.car_model.reparentTo(self.render)  # Preserve the imported hierarchy.

        # Build an index once, then derive livery targets from slot configuration.
        # No body or wing object name is hard-coded in the viewer.
        geom_nodes: dict[str, list[Any]] = {}
        for node_path in self.car_model.findAllMatches("**/+GeomNode"):
            geom_nodes.setdefault(node_path.getName(), []).append(node_path)

        target_names = sorted({slot["object"] for slot in self.slots.values()})  # Config-driven.
        missing_targets = []
        for name in target_names:
            matches = geom_nodes.get(name, [])
            if not matches:
                missing_targets.append(name)
            self.livery_nodes.extend(matches)
        if missing_targets:
            raise RuntimeError(
                "GLB does not contain calibrated livery node(s): "
                + ", ".join(missing_targets)
            )

        self._print_livery_node_transforms(target_names, geom_nodes)
        self._orient_center_and_scale_model_root()

        # Wheels are excluded from texture overrides and retain their black GLB
        # material even when the body texture is refreshed.
        self.wheel_nodes = [
            node
            for name, nodes in geom_nodes.items()
            if name.casefold().startswith("wheel")
            for node in nodes
        ]
        for wheel in self.wheel_nodes:
            wheel.setTextureOff(100)  # Override lower-priority inherited textures.

        material_map = self._read_glb_node_materials(self.model_path)
        print("[INFO] Dynamic livery nodes/materials:")
        for name in target_names:
            materials = material_map.get(name, [])
            material_text = ", ".join(materials) if materials else "unreported"
            print(f"  {name} -> {material_text}")
        print(f"[INFO] Wheel geometry retained as black: {len(self.wheel_nodes)} node(s)")

    def _print_livery_node_transforms(
        self, target_names: list[str], geom_nodes: dict[str, list[Any]]
    ) -> None:
        """Print imported hierarchy details before applying the root transform."""
        print("[INFO] Imported livery hierarchy/local transforms:")
        for name in target_names:
            for node in geom_nodes[name]:
                parent = node.getParent()
                print(
                    f"  node={name} parent={parent.getName()} "
                    f"pos={tuple(round(value, 6) for value in node.getPos())} "
                    f"hpr={tuple(round(value, 6) for value in node.getHpr())} "
                    f"scale={tuple(round(value, 6) for value in node.getScale())}"
                )

    def _orient_center_and_scale_model_root(self) -> None:
        """Apply presentation transforms only to the loader-returned model root."""
        bounds = self.car_model.getTightBounds()
        if not bounds:
            raise RuntimeError("Could not calculate bounds for the F1 car model")

        lower, upper = bounds
        dimensions = upper - lower
        values = (dimensions.x, dimensions.y, dimensions.z)

        # Detect this game model's length-Z/height-Y arrangement by proportion.
        if values.index(max(values)) == 2 and values.index(min(values)) == 1:
            self.car_model.setP(-90)  # Lay a length-on-Z export onto the ground.

        lower, upper = self.car_model.getTightBounds()
        dimensions = upper - lower
        horizontal_length = max(dimensions.x, dimensions.y)
        if horizontal_length <= 0:
            raise RuntimeError("F1 car model has invalid zero-size bounds")

        scale = 7.5 / horizontal_length  # Normalize cars with different units.
        self.car_model.setScale(scale)  # Transform only the loaded model root.

        # Recalculate scaled bounds, then center the complete car and place its
        # lowest point on the ground without touching any imported child node.
        lower, upper = self.car_model.getTightBounds()
        self.car_model.setPos(
            -(lower.x + upper.x) * 0.5,
            -(lower.y + upper.y) * 0.5,
            -lower.z,
        )

        print(
            "[INFO] Overall model-root transform: "
            f"pos={tuple(round(value, 6) for value in self.car_model.getPos())} "
            f"hpr={tuple(round(value, 6) for value in self.car_model.getHpr())} "
            f"scale={tuple(round(value, 6) for value in self.car_model.getScale())}"
        )

    def _setup_camera(self) -> None:
        bounds = self.car_model.getTightBounds()
        if not bounds:
            raise RuntimeError("Could not calculate orbit bounds for the F1 car model")

        lower, upper = bounds
        dimensions = upper - lower
        self.orbit_target = Point3(
            (lower.x + upper.x) * 0.5,
            (lower.y + upper.y) * 0.5,
            (lower.z + upper.z) * 0.5,
        )
        model_radius = max(dimensions.length() * 0.5, 0.1)
        self.minimum_distance = model_radius * 1.15  # Keep camera outside the car.
        self.maximum_distance = model_radius * 8.0  # Allow a useful overview.
        self.default_distance = model_radius * 2.85  # Fit the bounding sphere at 45° FOV.

        self.camera.reparentTo(self.render)  # Camera moves independently of the car.
        if self.camLens is not None:
            self.camLens.setNearFar(
                max(0.02, self.minimum_distance * 0.02),
                self.maximum_distance * 2.0,
            )
        self.reset_camera()

    def _setup_controls(self) -> None:
        # Camera interaction changes only yaw, pitch, and distance.
        self.accept("escape", self.userExit)
        self.accept("mouse1", self._start_orbit)  # Begin left-button orbit.
        self.accept("mouse1-up", self._stop_orbit)  # End left-button orbit.
        self.accept("wheel_up", self._zoom, [-1.0])  # Move camera inward.
        self.accept("wheel_down", self._zoom, [1.0])  # Move camera outward.
        self.accept("r", self.reset_camera)
        self.taskMgr.add(self._orbit_task, "camera-orbit")

    def _start_orbit(self) -> None:
        self.orbiting = True
        self.last_mouse = self._mouse_position()

    def _stop_orbit(self) -> None:
        self.orbiting = False
        self.last_mouse = None

    def _mouse_position(self) -> tuple[float, float] | None:
        if not self.mouseWatcherNode.hasMouse():
            return None
        mouse = self.mouseWatcherNode.getMouse()
        return mouse.x, mouse.y

    def _orbit_task(self, task):
        if not self.orbiting:
            return task.cont
        current = self._mouse_position()
        if current is None:
            return task.cont
        if self.last_mouse is not None:
            dx = current[0] - self.last_mouse[0]
            dy = current[1] - self.last_mouse[1]
            self._apply_orbit_delta(dx, dy)
        self.last_mouse = current
        return task.cont

    def _apply_orbit_delta(self, dx: float, dy: float) -> None:
        """Convert normalized mouse movement into clamped orbit angles."""
        self.yaw = (self.yaw - dx * 120.0) % 360.0
        self.pitch = max(-80.0, min(80.0, self.pitch + dy * 100.0))
        self._update_camera()

    def _zoom(self, direction: float) -> None:
        factor = 0.88 if direction < 0 else 1.14
        self.distance = max(
            self.minimum_distance,
            min(self.maximum_distance, self.distance * factor),
        )
        self._update_camera()

    def reset_camera(self) -> None:
        """Restore the initial orbit angles and model-derived zoom distance."""
        self.yaw = self.default_yaw
        self.pitch = self.default_pitch
        self.distance = self.default_distance
        self._update_camera()

    def _update_camera(self) -> None:
        """Place the camera on a sphere around the complete car bounds."""
        yaw_radians = math.radians(self.yaw)
        pitch_radians = math.radians(self.pitch)
        horizontal_distance = self.distance * math.cos(pitch_radians)
        camera_position = Point3(
            self.orbit_target.x + horizontal_distance * math.sin(yaw_radians),
            self.orbit_target.y - horizontal_distance * math.cos(yaw_radians),
            self.orbit_target.z + self.distance * math.sin(pitch_radians),
        )
        self.camera.setPos(self.render, camera_position)
        self.camera.lookAt(self.render, self.orbit_target)
        self.camera.setR(0)  # Explicitly prevent roll after every orbit update.

    def _setup_ui(self) -> None:
        # Menu entries are populated directly from configuration insertion order.
        panel = DirectFrame(
            parent=self.a2dTopRight,
            frameColor=(0.035, 0.045, 0.06, 0.94),
            frameSize=(-1.08, 0.0, -1.30, 0.0),
            pos=(-0.04, 0, -0.04),
        )
        DirectLabel(
            parent=panel,
            text="Sponsor Editor",
            text_align=0,
            text_scale=0.065,
            text_fg=(0.96, 0.97, 1.0, 1.0),
            frameColor=(0, 0, 0, 0),
            pos=(-0.54, 0, -0.10),
        )
        DirectLabel(
            parent=panel,
            text="Sponsor Slot:",
            text_align=-1,
            text_scale=0.045,
            text_fg=(0.82, 0.86, 0.92, 1.0),
            frameColor=(0, 0, 0, 0),
            pos=(-1.00, 0, -0.22),
        )
        self.slot_menu = DirectOptionMenu(
            parent=panel,
            items=list(self.slots),
            initialitem=0,
            command=self._select_slot,
            scale=0.045,
            text_align=-1,
            frameSize=(-0.1, 21.5, -0.75, 1.05),
            pos=(-0.98, 0, -0.32),
        )
        DirectLabel(
            parent=panel,
            text="Sponsor:",
            text_align=-1,
            text_scale=0.045,
            text_fg=(0.82, 0.86, 0.92, 1.0),
            frameColor=(0, 0, 0, 0),
            pos=(-1.00, 0, -0.48),
        )

        self.sponsor_labels = {
            f"{data.get('name', sponsor_id)} [{sponsor_id}]": sponsor_id
            for sponsor_id, data in self.sponsors.items()
        }
        sponsor_items = list(self.sponsor_labels)
        self.sponsor_menu = DirectOptionMenu(
            parent=panel,
            items=sponsor_items,
            initialitem=0,
            command=self._select_sponsor,
            scale=0.045,
            text_align=-1,
            frameSize=(-0.1, 21.5, -0.75, 1.05),
            pos=(-0.98, 0, -0.58),
        )

        DirectButton(
            parent=panel,
            text="Apply Sponsor",
            command=self._apply_selected_sponsor,
            scale=0.05,
            text_scale=0.9,
            frameSize=(-4.5, 4.5, -0.8, 1.15),
            pos=(-0.78, 0, -0.78),
        )
        DirectButton(
            parent=panel,
            text="Remove Sponsor",
            command=self._remove_selected_sponsor,
            scale=0.05,
            text_scale=0.9,
            frameSize=(-4.7, 4.7, -0.8, 1.15),
            pos=(-0.30, 0, -0.78),
        )
        DirectButton(
            parent=panel,
            text="Save Assignments",
            command=self._save_assignments,
            scale=0.05,
            text_scale=0.9,
            frameSize=(-5.0, 5.0, -0.8, 1.15),
            pos=(-0.54, 0, -0.94),
        )
        self.status_label = DirectLabel(
            parent=panel,
            text="Ready",
            text_align=-1,
            text_scale=0.037,
            text_wordwrap=27,
            text_fg=(0.70, 0.86, 0.72, 1.0),
            frameColor=(0, 0, 0, 0),
            pos=(-1.00, 0, -1.10),
        )
        DirectLabel(
            parent=self.a2dBottomLeft,
            text="Left-drag: orbit   Mouse wheel: zoom   R: reset   Esc: quit",
            text_align=-1,
            text_scale=0.04,
            text_fg=(0.86, 0.88, 0.92, 1.0),
            frameColor=(0.02, 0.025, 0.035, 0.72),
            pos=(0.05, 0, 0.06),
        )

        self._sync_sponsor_menu_to_slot()

    def _select_slot(self, slot_name: str) -> None:
        self.selected_slot = slot_name  # Change only the editor selection.
        if hasattr(self, "sponsor_menu"):
            self._sync_sponsor_menu_to_slot()

    def _select_sponsor(self, label: str) -> None:
        self.selected_sponsor = self.sponsor_labels[label]  # Display label to id.

    def _sync_sponsor_menu_to_slot(self) -> None:
        sponsor_id = self.assignments.get(self.selected_slot)
        if sponsor_id is None:
            return
        labels = list(self.sponsor_labels)
        for index, label in enumerate(labels):
            if self.sponsor_labels[label] == sponsor_id:
                self.sponsor_menu.set(index)
                self.selected_sponsor = sponsor_id
                return

    def _apply_selected_sponsor(self) -> None:
        # Preserve the prior value so a failed generation cannot corrupt editor
        # state or affect any assignment other than the selected slot.
        previous = self.assignments.get(self.selected_slot)
        self.assignments[self.selected_slot] = self.selected_sponsor  # One-slot edit.
        try:
            self.refresh_livery()
        except Exception as error:
            if previous is None:
                self.assignments.pop(self.selected_slot, None)
            else:
                self.assignments[self.selected_slot] = previous
            self._set_status(f"Apply failed: {error}", error=True)
            print(f"[ERROR] Livery refresh failed: {error}")
            return
        name = self.sponsors[self.selected_sponsor].get("name", self.selected_sponsor)
        self._set_status(f"Applied {name} to {self.selected_slot}")

    def _remove_selected_sponsor(self) -> None:
        # Removal follows the same rollback rule as assignment.
        previous = self.assignments.pop(self.selected_slot, None)  # Clear one slot.
        try:
            self.refresh_livery()
        except Exception as error:
            if previous is not None:
                self.assignments[self.selected_slot] = previous
            self._set_status(f"Remove failed: {error}", error=True)
            print(f"[ERROR] Livery refresh failed: {error}")
            return
        self._set_status(f"Cleared {self.selected_slot}")

    def _save_assignments(self) -> None:
        # Keep the stable slot order in the saved JSON and replace it atomically.
        ordered = {
            slot_name: self.assignments[slot_name]
            for slot_name in self.slots
            if slot_name in self.assignments
        }
        temporary = self.assignments_path.with_suffix(".json.tmp")  # Atomic save staging.
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(ordered, handle, indent=4)
                handle.write("\n")
            temporary.replace(self.assignments_path)
        except OSError as error:
            self._set_status(f"Save failed: {error}", error=True)
            print(f"[ERROR] Could not save assignments: {error}")
            return
        self._set_status(f"Saved {len(ordered)} assignments")
        print(f"[INFO] Assignments saved: {self.assignments_path}")

    def _set_status(self, message: str, error: bool = False) -> None:
        if hasattr(self, "status_label"):
            color = (1.0, 0.48, 0.42, 1.0) if error else (0.70, 0.86, 0.72, 1.0)
            self.status_label["text"] = message
            self.status_label["text_fg"] = color

    def refresh_livery(self) -> Path:
        """Regenerate, reload, and apply the current production livery."""
        try:
            # Delegate every placement operation to the production generator.
            generate_team_base(self.team, self.base_texture_path)  # Fresh clean base.
            generator = LiveryGenerator(self.base_texture_path, self.slots)  # Shared pipeline.
            output = generator.generate(
                assignments=self.assignments,
                sponsor_data=self.generator_sponsors,
                output_path=self.livery_texture_path,
            )
            # A newly allocated Texture bypasses Panda3D's filename cache.
            texture = self._load_texture_without_cache(output)
            for node in self.livery_nodes:
                node.setTexture(TextureStage.getDefault(), texture, 100)  # Replace GLB livery.
            self.current_texture = texture  # Retain the active texture reference.
        except Exception as error:
            raise RuntimeError(f"Could not regenerate or reload livery: {error}") from error

        print(
            f"[INFO] Livery refreshed (revision {self.texture_revision}, "
            f"{len(self.assignments)} sponsor placements): {output}"
        )
        return output

    def _load_texture_without_cache(self, path: Path) -> Texture:
        if not path.is_file():
            raise FileNotFoundError(f"Generated livery texture is missing: {path}")
        self.texture_revision += 1  # Ensure the texture name is never reused.
        texture = Texture(f"runtime_livery_{self.texture_revision}")  # Skip pool cache.
        filename = Filename.fromOsSpecific(str(path.resolve()))
        if not texture.read(filename):
            raise RuntimeError(f"Panda3D could not read generated texture: {path}")
        texture.setMinfilter(Texture.FTLinear)
        texture.setMagfilter(Texture.FTLinear)
        return texture

    @staticmethod
    def _read_glb_node_materials(path: Path) -> dict[str, list[str]]:
        """Read node/material names from GLB JSON metadata for startup reporting."""
        try:
            data = path.read_bytes()
            if len(data) < 20 or data[:4] != b"glTF":
                return {}
            offset = 12
            document = None
            while offset + 8 <= len(data):
                length, chunk_type = struct.unpack_from("<II", data, offset)
                offset += 8
                payload = data[offset : offset + length]
                offset += length
                if chunk_type == 0x4E4F534A:
                    document = json.loads(payload.rstrip(b"\x00 ").decode("utf-8"))
                    break
            if document is None:
                return {}

            materials = document.get("materials", [])
            meshes = document.get("meshes", [])
            result = {}
            for node in document.get("nodes", []):
                name = node.get("name")
                mesh_index = node.get("mesh")
                if not isinstance(name, str) or not isinstance(mesh_index, int):
                    continue
                names = []
                for primitive in meshes[mesh_index].get("primitives", []):
                    material_index = primitive.get("material")
                    if isinstance(material_index, int):
                        material_name = materials[material_index].get(
                            "name", f"material_{material_index}"
                        )
                        if material_name not in names:
                            names.append(material_name)
                result[name] = names
            return result
        except (OSError, ValueError, KeyError, IndexError, struct.error):
            return {}

    def run_viewer(self) -> None:
        self.run()


def main() -> int:
    try:
        viewer = CarViewer()
        viewer.run_viewer()
    except Exception as error:
        print(f"[ERROR] Sponsor editor could not start: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

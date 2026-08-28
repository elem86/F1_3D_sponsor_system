from __future__ import annotations

import json
import math
import shutil
import struct
from pathlib import Path
from typing import Any

from direct.gui import DirectGuiGlobals as DGG
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
from PIL import Image

from livery.config_loader import load_json
from livery.generator import LiveryGenerator


MODEL_PROFILE = Path("config/models/f2002/model.json")


class ViewerConfigError(ValueError):
    """Raised when model or livery configuration is incomplete or inconsistent."""


class CarViewer(ShowBase):
    """Display the F2002 car and edit its model-specific sponsor assignments."""

    def __init__(self, project_root: str | Path | None = None):
        # Resolve every input from the checkout so launching elsewhere is safe.
        self.project_root = Path(project_root or Path(__file__).resolve().parents[1])
        self.project_root = self.project_root.resolve()
        self.window_title = "F2002 Sponsor Editor"

        # Model-specific data stays together and never falls back to legacy slots.
        self.profile_path = self.project_root / MODEL_PROFILE
        self.profile = self._load_mapping(self.profile_path, "model profile")
        self.model_config_directory = self.profile_path.parent
        self.slots_path = self.model_config_directory / "sponsor_slots.json"
        self.assignments_path = self.model_config_directory / "demo_assignments.json"
        self.sponsors_path = self.project_root / "config" / "sponsors.json"
        self.slots = self._load_mapping(self.slots_path, "sponsor slots")
        self.assignments = self._load_mapping(self.assignments_path, "assignments")
        self.sponsors = self._load_mapping(self.sponsors_path, "sponsors")

        # The clean source is immutable; generated output always goes elsewhere.
        self.model_path = self._profile_asset("model")
        self.base_texture_path = self._profile_asset("clean_base_texture")
        self.steering_wheel_texture_path = self._profile_asset(
            "steering_wheel_texture"
        )
        self.team_path = self._profile_asset("team_identity")
        self.team = self._load_mapping(self.team_path, "team identity")
        self.production_livery_path = (
            self.project_root / "generated" / "f2002_team_livery.png"
        )
        self.runtime_texture_directory = (
            self.project_root / "generated" / "runtime_liveries"
        )
        self.livery_texture_path = self.production_livery_path
        self.texture_size = self._read_texture_size()
        self.root_hpr = self._read_root_hpr()
        self._validate_config()
        self.generator_sponsors = self._absolute_sponsor_paths()
        self.generator_team = self._absolute_team_asset_paths()

        super().__init__()

        # Keep runtime rendering, camera, and assignment state in one viewer.
        self.car_model = None
        self.livery_nodes: list[Any] = []
        self.wheel_nodes: list[Any] = []
        self.steering_wheel_nodes: list[Any] = []
        self.steering_wheel_texture: Texture | None = None
        self.current_texture: Texture | None = None
        self.texture_revision = 0
        self.orbiting = False
        self.last_mouse: tuple[float, float] | None = None
        self.orbit_target = Point3(0, 0, 0)
        self.model_radius = 1.0
        self.default_yaw = -28.0
        self.default_pitch = 18.0
        self.default_distance = 11.0
        self.yaw = self.default_yaw
        self.pitch = self.default_pitch
        self.distance = self.default_distance
        self.minimum_distance = 5.0
        self.maximum_distance = 24.0
        self.selected_slot = next(iter(self.slots), None)
        self.selected_sponsor = next(iter(self.sponsors), None)

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
        print(f"[INFO] F2002 slot count: {len(self.slots)}")
        print(f"[INFO] Current assignment count: {len(self.assignments)}")
        print(
            f"[INFO] Team identity: {self.team['name']} "
            f"#{self.team['driver_number']}"
        )
        print(f"[INFO] Production livery: {self.production_livery_path}")
        print(f"[INFO] Active Panda3D texture: {self.livery_texture_path}")

    @staticmethod
    def _load_mapping(path: Path, description: str) -> dict[str, Any]:
        """Load a required JSON object and provide a focused error message."""
        try:
            data = load_json(path)
        except json.JSONDecodeError as error:
            raise ViewerConfigError(
                f"Malformed {description} JSON at {path}: "
                f"line {error.lineno}, column {error.colno}: {error.msg}"
            ) from error
        except OSError as error:
            raise ViewerConfigError(
                f"Could not load {description} from {path}: {error}"
            ) from error
        if not isinstance(data, dict):
            raise ViewerConfigError(
                f"{description.capitalize()} config must be a JSON object: {path}"
            )
        return data

    def _profile_asset(self, field: str) -> Path:
        """Resolve one required repository-relative asset from the model profile."""
        value = self.profile.get(field)
        if not isinstance(value, str) or not value:
            raise ViewerConfigError(f"Model profile must define a non-empty {field!r}")
        path = (self.project_root / value).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Model profile asset is missing ({field}): {path}")
        return path

    def _read_texture_size(self) -> tuple[int, int]:
        """Validate the declared target atlas size."""
        value = self.profile.get("texture_size")
        if (
            not isinstance(value, list)
            or len(value) != 2
            or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
            or any(item <= 0 for item in value)
        ):
            raise ViewerConfigError("model.texture_size must contain two positive integers")
        return value[0], value[1]

    def _read_root_hpr(self) -> tuple[float, float, float]:
        """Read the one presentation correction applied to the loaded model root."""
        value = self.profile.get("root_hpr")
        if (
            not isinstance(value, list)
            or len(value) != 3
            or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value)
        ):
            raise ViewerConfigError("model.root_hpr must contain three numbers")
        return float(value[0]), float(value[1]), float(value[2])

    def _validate_config(self) -> None:
        """Validate shared sponsors and externally supplied F2002 slots."""
        if not self.sponsors:
            raise ViewerConfigError(f"No sponsors are defined in {self.sponsors_path}")

        team_name = self.team.get("name")
        driver_number = self.team.get("driver_number")
        assets = self.team.get("assets")
        if not isinstance(team_name, str) or not team_name:
            raise ViewerConfigError("Team identity must define a non-empty name")
        if not isinstance(driver_number, (str, int)):
            raise ViewerConfigError("Team identity driver_number must be text or an integer")
        if not isinstance(assets, dict) or not assets:
            raise ViewerConfigError("Team identity must define branding assets")

        # An empty map is valid before Blender-authored slots are supplied.
        for slot_name, slot in self.slots.items():
            if not isinstance(slot_name, str) or not slot_name:
                raise ViewerConfigError("Every sponsor slot must have a non-empty name")
            if not isinstance(slot, dict):
                raise ViewerConfigError(f"Slot {slot_name!r} must be a JSON object")
            if not isinstance(slot.get("object"), str) or not slot["object"]:
                raise ViewerConfigError(
                    f"Slot {slot_name!r} must define a non-empty object name"
                )

        missing_logos: list[str] = []
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
                    "Every assignment must map a string slot name to a sponsor id"
                )
        unknown_slots = sorted(set(self.assignments) - set(self.slots))
        unknown_sponsors = sorted(set(self.assignments.values()) - set(self.sponsors))
        if unknown_slots:
            raise ViewerConfigError(
                f"Assignments reference unknown F2002 slot(s): {', '.join(unknown_slots)}"
            )
        if unknown_sponsors:
            raise ViewerConfigError(
                f"Assignments reference unknown sponsor(s): {', '.join(unknown_sponsors)}"
            )

        # The production base must remain a native, completely opaque RGB atlas.
        with Image.open(self.base_texture_path) as image:
            if image.size != self.texture_size:
                raise ViewerConfigError(
                    f"Clean base is {image.size}, expected {self.texture_size}: "
                    f"{self.base_texture_path}"
                )
            if image.mode != "RGB":
                raise ViewerConfigError(
                    f"Clean base must be opaque RGB, found {image.mode}: "
                    f"{self.base_texture_path}"
                )

    def _absolute_sponsor_paths(self) -> dict[str, Any]:
        """Make logo paths independent of the process working directory."""
        resolved: dict[str, Any] = {}
        for sponsor_id, sponsor in self.sponsors.items():
            entry = dict(sponsor)
            logo_path = Path(entry["logo"])
            if not logo_path.is_absolute():
                logo_path = self.project_root / logo_path
            entry["logo"] = str(logo_path.resolve())
            resolved[sponsor_id] = entry
        return resolved

    def _absolute_team_asset_paths(self) -> dict[str, Any]:
        """Resolve team marks once so livery refreshes are launch-directory safe."""
        resolved = dict(self.team)
        assets: dict[str, str] = {}
        for asset_id, configured_path in self.team["assets"].items():
            if not isinstance(asset_id, str) or not isinstance(configured_path, str):
                raise ViewerConfigError("Team asset ids and paths must be strings")
            asset_path = Path(configured_path)
            if not asset_path.is_absolute():
                asset_path = self.project_root / asset_path
            if not asset_path.is_file():
                raise FileNotFoundError(
                    f"Team branding asset is missing ({asset_id}): {asset_path}"
                )
            assets[asset_id] = str(asset_path.resolve())
        resolved["assets"] = assets
        return resolved

    def _setup_window(self) -> None:
        """Configure a neutral window before adding scene content."""
        self.disableMouse()
        self.setBackgroundColor(0.12, 0.14, 0.17, 1.0)
        if self.win is not None and hasattr(self.win, "requestProperties"):
            properties = WindowProperties()
            properties.setTitle(self.window_title)
            self.win.requestProperties(properties)
        if self.camLens is not None:
            self.camLens.setFov(45)
            self.camLens.setNearFar(0.05, 250.0)

    def _setup_lights(self) -> None:
        """Add broad neutral lighting suitable for inspecting the whole car."""
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
        """Load the GLB once and preserve every imported child transform."""
        panda_path = Filename.fromOsSpecific(str(self.model_path))
        try:
            model = self.loader.loadModel(panda_path)
        except Exception as error:
            raise RuntimeError(
                f"Panda3D could not load GLB {self.model_path}: {error}"
            ) from error
        if model is None or model.isEmpty():
            raise RuntimeError(f"Panda3D returned an empty model for {self.model_path}")

        self.car_model = model
        self.car_model.reparentTo(self.render)
        self._print_node_hierarchy_once()
        self._print_node_roles()
        self._orient_center_and_scale_model_root()

        # Apply the livery only to body and aero meshes. Wheels receive explicit
        # dark overrides so the pure-white atlas cannot turn the tyres white.
        geometry_nodes = list(self.car_model.findAllMatches("**/+GeomNode"))
        if not geometry_nodes:
            raise RuntimeError("F2002 GLB contains no renderable geometry nodes")
        roles = self.profile["node_roles"]
        tyre_names = set(roles.get("front_wheels", [])) | set(
            roles.get("rear_wheels", [])
        )
        rim_names = set(roles.get("front_rims_hubs", [])) | set(
            roles.get("rear_rims_hubs", [])
        )
        wheel_names = tyre_names | rim_names
        steering_names = set(roles.get("steering_wheel", []))
        self.wheel_nodes = [
            node for node in geometry_nodes if node.getName() in wheel_names
        ]
        self.steering_wheel_nodes = [
            node for node in geometry_nodes if node.getName() in steering_names
        ]
        if not self.steering_wheel_nodes:
            raise RuntimeError("Configured F2002 steering-wheel node was not found")
        self.livery_nodes = [
            node
            for node in geometry_nodes
            if node.getName() not in (wheel_names | steering_names)
        ]
        if not self.livery_nodes:
            raise RuntimeError("F2002 GLB contains no body/aero livery geometry")

        # High-priority flat colors replace embedded material textures on wheels.
        for node in self.wheel_nodes:
            node.setTextureOff(200)
            node.setMaterialOff(200)
            if node.getName() in tyre_names:
                node.setColor(0.025, 0.03, 0.04, 1.0, 201)
            else:
                node.setColor(0.11, 0.12, 0.14, 1.0, 201)

        # Plane.024 is the actual steering-wheel mesh. Keep its source UV look
        # instead of whitening it with the mutable body sponsor atlas.
        steering_texture = Texture("f2002_steering_wheel")
        steering_filename = Filename.fromOsSpecific(
            str(self.steering_wheel_texture_path.resolve())
        )
        if not steering_texture.read(steering_filename):
            raise RuntimeError(
                f"Could not load steering-wheel texture: "
                f"{self.steering_wheel_texture_path}"
            )
        steering_texture.setMinfilter(Texture.FTLinearMipmapLinear)
        steering_texture.setMagfilter(Texture.FTLinear)
        for node in self.steering_wheel_nodes:
            node.setTextureOff(200)
            node.setTexture(TextureStage.getDefault(), steering_texture, 201)
        self.steering_wheel_texture = steering_texture

        print(f"[INFO] Dynamic atlas targets: {len(self.livery_nodes)} body/aero nodes")
        print(f"[INFO] Dark wheel overrides: {len(self.wheel_nodes)} geometry nodes")
        print(
            f"[INFO] Steering wheel: {len(self.steering_wheel_nodes)} node(s), "
            f"source={self.steering_wheel_texture_path}"
        )

    def _print_node_hierarchy_once(self) -> None:
        """Report imported local transforms before the model root is presented."""
        print("[INFO] Imported GLB hierarchy and local transforms:")

        def visit(node_path, depth: int) -> None:
            indent = "  " * depth
            print(
                f"{indent}{node_path.getName()} [{node_path.node().getType().getName()}] "
                f"pos={self._rounded_tuple(node_path.getPos())} "
                f"hpr={self._rounded_tuple(node_path.getHpr())} "
                f"scale={self._rounded_tuple(node_path.getScale())}"
            )
            for child in node_path.getChildren():
                visit(child, depth + 1)

        visit(self.car_model, 0)

    def _print_node_roles(self) -> None:
        """Report inspected semantic roles without renaming source GLB nodes."""
        roles = self.profile.get("node_roles", {})
        if not isinstance(roles, dict):
            raise ViewerConfigError("model.node_roles must be a JSON object")
        existing = {node.getName() for node in self.car_model.findAllMatches("**/*")}
        material_map = self._read_glb_node_materials(self.model_path)
        print("[INFO] Inspected F2002 node roles:")
        for role, names in roles.items():
            if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
                raise ViewerConfigError(f"node_roles.{role} must be a list of names")
            for name in names:
                status = "found" if name in existing else "MISSING"
                materials = ", ".join(material_map.get(name, [])) or "unreported"
                print(f"  {role}: {name} ({status}, material={materials})")

    @staticmethod
    def _rounded_tuple(vector) -> tuple[float, ...]:
        return tuple(round(float(value), 6) for value in vector)

    def _orient_center_and_scale_model_root(self) -> None:
        """Apply correction, centering, and scale only to the loader root."""
        print(
            "[INFO] Model root HPR before correction: "
            f"{self._rounded_tuple(self.car_model.getHpr())}"
        )
        print(f"[INFO] Model-root orientation correction: {self.root_hpr}")
        self.car_model.setHpr(*self.root_hpr)
        print(
            "[INFO] Model root HPR after correction: "
            f"{self._rounded_tuple(self.car_model.getHpr())}"
        )

        bounds = self.car_model.getTightBounds()
        if not bounds:
            raise RuntimeError("Could not calculate bounds for the F2002 car")
        lower, upper = bounds
        dimensions = upper - lower
        horizontal_length = max(dimensions.x, dimensions.y)
        if horizontal_length <= 0:
            raise RuntimeError("F2002 car has invalid zero-size bounds")

        self.car_model.setScale(7.5 / horizontal_length)
        lower, upper = self.car_model.getTightBounds()
        self.car_model.setPos(
            -(lower.x + upper.x) * 0.5,
            -(lower.y + upper.y) * 0.5,
            -lower.z,
        )
        print(
            "[INFO] Overall model-root transform: "
            f"pos={self._rounded_tuple(self.car_model.getPos())} "
            f"hpr={self._rounded_tuple(self.car_model.getHpr())} "
            f"scale={self._rounded_tuple(self.car_model.getScale())}"
        )

    def _setup_camera(self) -> None:
        """Derive an orbit target and zoom range from the corrected whole-car bounds."""
        bounds = self.car_model.getTightBounds()
        if not bounds:
            raise RuntimeError("Could not calculate orbit bounds for the F2002 car")
        lower, upper = bounds
        dimensions = upper - lower
        self.orbit_target = Point3(
            (lower.x + upper.x) * 0.5,
            (lower.y + upper.y) * 0.5,
            (lower.z + upper.z) * 0.5,
        )
        self.model_radius = max(dimensions.length() * 0.5, 0.1)
        self.minimum_distance = self.model_radius * 1.15
        self.maximum_distance = self.model_radius * 8.0
        self.default_distance = self.model_radius * 2.85

        self.camera.reparentTo(self.render)
        if self.camLens is not None:
            self.camLens.setNearFar(
                max(0.02, self.minimum_distance * 0.02),
                self.maximum_distance * 2.0,
            )
        self.reset_camera()

    def _setup_controls(self) -> None:
        """Bind orbit, zoom, reset, and quit without rotating the car."""
        self.accept("escape", self.userExit)
        self.accept("mouse1", self._start_orbit)
        self.accept("mouse1-up", self._stop_orbit)
        self.accept("wheel_up", self._zoom, [-1.0])
        self.accept("wheel_down", self._zoom, [1.0])
        self.accept("r", self.reset_camera)
        self.taskMgr.add(self._orbit_task, "camera-orbit")

    def _start_orbit(self) -> None:
        self.orbiting = True
        self.last_mouse = self._mouse_position()

    def _stop_orbit(self) -> None:
        self.orbiting = False
        self.last_mouse = None

    def _mouse_position(self) -> tuple[float, float] | None:
        if self.mouseWatcherNode is None or not self.mouseWatcherNode.hasMouse():
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
        self.yaw = self.default_yaw
        self.pitch = self.default_pitch
        self.distance = self.default_distance
        self._update_camera()

    def _update_camera(self) -> None:
        """Place the camera on a sphere and force zero roll."""
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
        self.camera.setR(0)

    def _setup_ui(self) -> None:
        """Build the runtime assignment UI from the current configuration."""
        panel = DirectFrame(
            parent=self.a2dTopRight,
            frameColor=(0.035, 0.045, 0.06, 0.94),
            frameSize=(-1.08, 0.0, -1.30, 0.0),
            pos=(-0.04, 0, -0.04),
        )
        DirectLabel(
            parent=panel,
            text=f"{self.team['name']} Sponsor Editor",
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

        slot_items = list(self.slots) or ["(no F2002 slots configured)"]
        self.slot_menu = DirectOptionMenu(
            parent=panel,
            items=slot_items,
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

        button_state = DGG.NORMAL if self.slots else DGG.DISABLED
        DirectButton(
            parent=panel,
            text="Apply Sponsor",
            command=self._apply_selected_sponsor,
            state=button_state,
            scale=0.05,
            text_scale=0.9,
            frameSize=(-4.5, 4.5, -0.8, 1.15),
            pos=(-0.78, 0, -0.78),
        )
        DirectButton(
            parent=panel,
            text="Remove Sponsor",
            command=self._remove_selected_sponsor,
            state=button_state,
            scale=0.05,
            text_scale=0.9,
            frameSize=(-4.7, 4.7, -0.8, 1.15),
            pos=(-0.30, 0, -0.78),
        )
        DirectButton(
            parent=panel,
            text="Save Assignments",
            command=self._save_assignments,
            state=button_state,
            scale=0.05,
            text_scale=0.9,
            frameSize=(-5.0, 5.0, -0.8, 1.15),
            pos=(-0.54, 0, -0.94),
        )
        initial_status = (
            "Ready"
            if self.slots
            else "Add slots in config/models/f2002/sponsor_slots.json"
        )
        self.status_label = DirectLabel(
            parent=panel,
            text=initial_status,
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
        if self.selected_slot is not None:
            self._sync_sponsor_menu_to_slot()

    def _select_slot(self, slot_name: str) -> None:
        if slot_name not in self.slots:
            return
        self.selected_slot = slot_name
        if hasattr(self, "sponsor_menu"):
            self._sync_sponsor_menu_to_slot()

    def _select_sponsor(self, label: str) -> None:
        sponsor_id = self.sponsor_labels.get(label)
        if sponsor_id is not None:
            self.selected_sponsor = sponsor_id

    def _sync_sponsor_menu_to_slot(self) -> None:
        if self.selected_slot is None:
            return
        sponsor_id = self.assignments.get(self.selected_slot)
        if sponsor_id is None:
            return
        for index, label in enumerate(self.sponsor_labels):
            if self.sponsor_labels[label] == sponsor_id:
                self.sponsor_menu.set(index)
                self.selected_sponsor = sponsor_id
                return

    def _apply_selected_sponsor(self) -> None:
        if self.selected_slot is None or self.selected_sponsor is None:
            self._set_status("No configured slot or sponsor is selected", error=True)
            return
        previous = self.assignments.get(self.selected_slot)
        self.assignments[self.selected_slot] = self.selected_sponsor
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
        if self.selected_slot is None:
            self._set_status("No configured slot is selected", error=True)
            return
        previous = self.assignments.pop(self.selected_slot, None)
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
        """Persist only known F2002 slots using an atomic file replacement."""
        ordered = {
            slot_name: self.assignments[slot_name]
            for slot_name in self.slots
            if slot_name in self.assignments
        }
        temporary = self.assignments_path.with_suffix(".json.tmp")
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
        """Rebuild from the clean atlas, reload it, and update body/aero meshes."""
        next_revision = self.texture_revision + 1
        runtime_output = (
            self.runtime_texture_directory / f"runtime_livery_{next_revision:04d}.png"
        )
        previous_runtime = self.livery_texture_path
        previous_texture = self.current_texture
        try:
            # Native scale preserves the required 2024 atlas and avoids 256 output.
            generator = LiveryGenerator(
                self.base_texture_path,
                self.slots,
                working_scale=1,
                output_mode="RGB",
            )
            production_output = generator.generate(
                assignments=dict(self.assignments),
                sponsor_data=self.generator_sponsors,
                output_path=self.production_livery_path,
                team_data=self.generator_team,
            )

            # A unique filename prevents Panda3D's texture pool from returning the
            # previous image even though the production filename stays stable.
            runtime_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(production_output, runtime_output)
            texture = self._load_texture_without_cache(runtime_output, next_revision)
            for node in self.livery_nodes:
                node.setTextureOff(100)
                node.setTexture(TextureStage.getDefault(), texture, 101)

            self.current_texture = texture
            self.texture_revision = next_revision
            self.livery_texture_path = runtime_output
            if previous_texture is not None:
                previous_texture.releaseAll()
                previous_texture.clear()
            self._cleanup_runtime_texture_files(keep=runtime_output)
        except Exception as error:
            if runtime_output.exists() and runtime_output != previous_runtime:
                runtime_output.unlink()
            raise RuntimeError(f"Could not regenerate or reload livery: {error}") from error

        print(
            f"[INFO] Livery refreshed (revision {self.texture_revision}, "
            f"{len(self.assignments)} sponsor placements): {self.production_livery_path}"
        )
        return self.production_livery_path

    def _load_texture_without_cache(self, path: Path, revision: int) -> Texture:
        if not path.is_file():
            raise FileNotFoundError(f"Generated livery texture is missing: {path}")
        texture = Texture(f"f2002_runtime_livery_{revision:04d}")
        filename = Filename.fromOsSpecific(str(path.resolve()))
        if not texture.read(filename):
            raise RuntimeError(f"Panda3D could not read generated texture: {path}")
        texture.setMinfilter(Texture.FTLinearMipmapLinear)
        texture.setMagfilter(Texture.FTLinear)
        return texture

    def _cleanup_runtime_texture_files(self, keep: Path) -> None:
        """Retain only the active cache-busting texture file."""
        self.runtime_texture_directory.mkdir(parents=True, exist_ok=True)
        for candidate in self.runtime_texture_directory.glob("runtime_livery_*.png"):
            if candidate.resolve() != keep.resolve():
                try:
                    candidate.unlink()
                except OSError as error:
                    print(
                        f"[WARNING] Could not remove stale runtime texture "
                        f"{candidate}: {error}"
                    )

    @staticmethod
    def _read_glb_node_materials(path: Path) -> dict[str, list[str]]:
        """Read node/material names from the GLB JSON chunk for reporting."""
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
            result: dict[str, list[str]] = {}
            for node in document.get("nodes", []):
                name = node.get("name")
                mesh_index = node.get("mesh")
                if not isinstance(name, str) or not isinstance(mesh_index, int):
                    continue
                names: list[str] = []
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

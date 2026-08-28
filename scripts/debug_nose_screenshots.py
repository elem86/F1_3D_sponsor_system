from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Filename,
    GraphicsPipe,
    Point3,
    Texture,
    TextureStage,
    WindowProperties,
    loadPrcFileData,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODEL_PROFILE = PROJECT_ROOT / "config" / "models" / "f2002" / "model.json"
import os
DEBUG_TEXTURE = Path(
    os.environ.get(
        "NOSE_DEBUG_TEXTURE",
        str(PROJECT_ROOT / "generated" / "debug" / "f2002_nose_label_livery.png"),
    )
)
SCREENSHOT_DIR = PROJECT_ROOT / "generated" / "debug" / "nose_screenshots"

loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", "audio-library-name null")
loadPrcFileData("", "win-size 1600 1200")


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class NoseInspector(ShowBase):
    def __init__(self) -> None:
        super().__init__(windowType="offscreen")
        profile = _load(MODEL_PROFILE)
        model_path = PROJECT_ROOT / profile["model"]
        root_hpr = tuple(profile["root_hpr"])
        roles = profile["node_roles"]

        self.setBackgroundColor(0.12, 0.14, 0.17, 1.0)
        self.disableMouse()
        if self.camLens is not None:
            self.camLens.setFov(40)
            self.camLens.setNearFar(0.02, 250.0)

        ambient = AmbientLight("ambient")
        ambient.setColor((0.4, 0.42, 0.46, 1.0))
        self.render.setLight(self.render.attachNewNode(ambient))
        key = DirectionalLight("key")
        key.setColor((1.0, 0.98, 0.94, 1.0))
        key_node = self.render.attachNewNode(key)
        key_node.setHpr(-35, -48, 0)
        self.render.setLight(key_node)
        fill = DirectionalLight("fill")
        fill.setColor((0.5, 0.55, 0.68, 1.0))
        fill_node = self.render.attachNewNode(fill)
        fill_node.setHpr(145, -22, 0)
        self.render.setLight(fill_node)

        panda_path = Filename.fromOsSpecific(str(model_path))
        model = self.loader.loadModel(panda_path)
        if model is None or model.isEmpty():
            raise RuntimeError(f"Could not load {model_path}")
        model.reparentTo(self.render)
        model.setHpr(*root_hpr)

        bounds = model.getTightBounds()
        lower, upper = bounds
        dimensions = upper - lower
        horizontal_length = max(dimensions.x, dimensions.y)
        model.setScale(7.5 / horizontal_length)
        lower, upper = model.getTightBounds()
        model.setPos(
            -(lower.x + upper.x) * 0.5,
            -(lower.y + upper.y) * 0.5,
            -lower.z,
        )

        geometry_nodes = list(model.findAllMatches("**/+GeomNode"))
        tyre_names = set(roles.get("front_wheels", [])) | set(roles.get("rear_wheels", []))
        rim_names = set(roles.get("front_rims_hubs", [])) | set(roles.get("rear_rims_hubs", []))
        wheel_names = tyre_names | rim_names
        steering_names = set(roles.get("steering_wheel", []))
        livery_nodes = [
            node for node in geometry_nodes
            if node.getName() not in (wheel_names | steering_names)
        ]

        for node in geometry_nodes:
            if node.getName() in wheel_names:
                node.setTextureOff(200)
                node.setMaterialOff(200)
                node.setColor(0.06, 0.06, 0.07, 1.0, 201)

        texture = Texture("debug_livery")
        texture_filename = Filename.fromOsSpecific(str(DEBUG_TEXTURE.resolve()))
        if not texture.read(texture_filename):
            raise RuntimeError(f"Could not load debug texture: {DEBUG_TEXTURE}")
        texture.setMinfilter(Texture.FTLinearMipmapLinear)
        texture.setMagfilter(Texture.FTLinear)
        for node in livery_nodes:
            node.setTextureOff(200)
            node.setTexture(TextureStage.getDefault(), texture, 201)

        self.model = model
        bounds = model.getTightBounds()
        lower, upper = bounds
        self.center = Point3(
            (lower.x + upper.x) * 0.5,
            (lower.y + upper.y) * 0.5,
            (lower.z + upper.z) * 0.5,
        )
        self.radius = max((upper - lower).length() * 0.5, 0.1)
        # front_wing (Circle.092) sits at the -Y extreme after root_hpr correction,
        # confirmed against config/models/f2002/model.json node_roles bounds.
        self.nose_point = Point3(
            (lower.x + upper.x) * 0.5,
            lower.y,
            lower.z + (upper.z - lower.z) * 0.35,
        )
        # rear_wing (Circle.094) sits at the +Y extreme, confirmed the same way.
        self.rear_point = Point3(
            (lower.x + upper.x) * 0.5,
            upper.y,
            lower.z + (upper.z - lower.z) * 0.55,
        )

    def shoot(self, name: str, target: Point3, yaw: float, pitch: float, distance: float) -> None:
        yaw_r = math.radians(yaw)
        pitch_r = math.radians(pitch)
        horizontal = distance * math.cos(pitch_r)
        camera_position = Point3(
            target.x + horizontal * math.sin(yaw_r),
            target.y - horizontal * math.cos(yaw_r),
            target.z + distance * math.sin(pitch_r),
        )
        self.camera.setPos(self.render, camera_position)
        self.camera.lookAt(self.render, target)
        self.camera.setR(0)
        self.graphicsEngine.renderFrame()
        self.graphicsEngine.renderFrame()
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        output = SCREENSHOT_DIR / f"{name}.png"
        self.win.saveScreenshot(Filename.fromOsSpecific(str(output)))
        print(f"Saved {output}")


def main() -> None:
    app = NoseInspector()
    nose = app.nose_point
    # Wide 3/4 shots first to confirm overall placement/orientation.
    app.shoot("nose_front_top", nose, yaw=0, pitch=35, distance=app.radius * 0.9)
    app.shoot("nose_left_side", nose, yaw=-70, pitch=15, distance=app.radius * 0.9)
    app.shoot("nose_right_side", nose, yaw=70, pitch=15, distance=app.radius * 0.9)
    app.shoot("nose_top_down", nose, yaw=0, pitch=75, distance=app.radius * 0.8)
    app.shoot("nose_front_close", nose, yaw=0, pitch=20, distance=app.radius * 0.5)
    app.shoot("nose_top_close", nose, yaw=0, pitch=55, distance=app.radius * 0.45)
    app.shoot("nose_number_close", nose, yaw=0, pitch=25, distance=app.radius * 0.28)
    # Straight-down orthographic-ish view centered slightly further back (toward
    # the cockpit) to catch the whole nose_top sponsor/wordmark/number strip.
    top_center = Point3(nose.x, nose.y + app.radius * 0.55, nose.z + app.radius * 0.05)
    app.shoot("nose_top_strip", top_center, yaw=0, pitch=85, distance=app.radius * 0.75)
    # Wider, further-back flank views: nose_left/right's UV maps to the wider
    # flank near the cockpit/front-wheel area, not the tapered nose tip.
    app.shoot("nose_flank_left", nose, yaw=-35, pitch=10, distance=app.radius * 1.4)
    app.shoot("nose_flank_right", nose, yaw=35, pitch=10, distance=app.radius * 1.4)

    rear = app.rear_point
    app.shoot("rearwing_rear", rear, yaw=180, pitch=20, distance=app.radius * 1.1)
    app.shoot("rearwing_rear_top", rear, yaw=180, pitch=45, distance=app.radius * 0.9)
    app.shoot("rearwing_rear_close", rear, yaw=180, pitch=15, distance=app.radius * 0.55)
    # Slightly elevated, further-back view looking down onto the rear wing's
    # top face (where rearwing_main's UV island actually paints), not the
    # underside seen from directly behind.
    app.shoot("rearwing_top_readable", rear, yaw=200, pitch=35, distance=app.radius * 0.8)


if __name__ == "__main__":
    main()

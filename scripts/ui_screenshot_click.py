from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from panda3d.core import Filename, loadPrcFileData

sponsor_id = sys.argv[1] if len(sys.argv) > 1 else "orbix"
output = sys.argv[2] if len(sys.argv) > 2 else "generated/debug/ui_click_test.png"

loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", "audio-library-name null")
loadPrcFileData("", "win-size 1920 1080")

from viewer.car_viewer import CarViewer

viewer = CarViewer()
viewer.graphicsEngine.renderFrame()

card = viewer.ui._sponsor_cards[sponsor_id]
card.button["command"](*card.button["extraArgs"])

viewer.graphicsEngine.renderFrame()
viewer.graphicsEngine.renderFrame()
output_path = PROJECT_ROOT / output
output_path.parent.mkdir(parents=True, exist_ok=True)
viewer.win.saveScreenshot(Filename.fromOsSpecific(str(output_path)))
print(f"Saved {output_path}, selected_sponsor={viewer.selected_sponsor}")

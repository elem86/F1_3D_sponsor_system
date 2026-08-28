from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from panda3d.core import Filename, loadPrcFileData

width = int(sys.argv[1]) if len(sys.argv) > 1 else 1920
height = int(sys.argv[2]) if len(sys.argv) > 2 else 1080
output = sys.argv[3] if len(sys.argv) > 3 else "generated/debug/ui_screenshot.png"

loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", "audio-library-name null")
loadPrcFileData("", f"win-size {width} {height}")

from viewer.car_viewer import CarViewer

viewer = CarViewer()
viewer.graphicsEngine.renderFrame()
viewer.graphicsEngine.renderFrame()
viewer.graphicsEngine.renderFrame()
output_path = PROJECT_ROOT / output
output_path.parent.mkdir(parents=True, exist_ok=True)
viewer.win.saveScreenshot(Filename.fromOsSpecific(str(output_path)))
print(f"Saved {output_path}")

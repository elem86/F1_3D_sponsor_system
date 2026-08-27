from __future__ import annotations

from pathlib import Path

from viewer.car_viewer import CarViewer


def main() -> int:
    """Start the interactive car viewer from the repository root."""
    try:
        viewer = CarViewer(project_root=Path(__file__).resolve().parent)  # Load this checkout.
        viewer.run_viewer()  # Enter Panda3D's event and rendering loop.
    except Exception as error:
        print(f"[ERROR] Sponsor editor could not start: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # Return startup failures to the calling shell.

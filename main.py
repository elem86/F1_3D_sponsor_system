from __future__ import annotations

from pathlib import Path

from viewer.car_viewer import CarViewer


def main() -> int:
    """Start the focused runtime sponsor viewer and assignment editor."""
    project_root = Path(__file__).resolve().parent
    try:
        viewer = CarViewer(project_root=project_root)
        viewer.run_viewer()
    except Exception as error:
        print(f"[ERROR] Sponsor editor could not start: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # Return startup failures to the calling shell.

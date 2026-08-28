from __future__ import annotations

from livery.app_paths import get_resource_root, get_writable_root
from viewer.car_viewer import CarViewer


def main() -> int:
    """Start the focused runtime sponsor viewer and assignment editor."""
    resource_root = get_resource_root()
    writable_root = get_writable_root()
    try:
        viewer = CarViewer(project_root=resource_root, writable_root=writable_root)
        viewer.run_viewer()
    except Exception as error:
        print(f"[ERROR] Sponsor editor could not start: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # Return startup failures to the calling shell.

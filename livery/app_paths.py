from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "F1SponsorSystem"

# Files under this relative path are seeded from the bundled default the
# first time the writable copy does not exist, then only ever read/written
# from the writable location afterward. Bundled JSON is never modified.
_SEEDED_WRITABLE_FILES = (
    Path("config") / "models" / "f2002" / "demo_assignments.json",
)


def is_frozen() -> bool:
    """True when running inside a PyInstaller-built executable."""
    return bool(getattr(sys, "frozen", False))


def get_resource_root() -> Path:
    """Return the root directory for read-only bundled resources.

    - Source/dev mode: the repository root (two levels above this file).
    - PyInstaller onedir/onefile mode: `sys._MEIPASS`, the directory
      PyInstaller extracts/exposes bundled data files into. This directory
      must be treated as read-only -- PyInstaller may re-create it on every
      launch (onefile) or ship it alongside a locked-down install (onedir).
    """
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_writable_root() -> Path:
    """Return the root directory for runtime-generated/user-writable files.

    - Source/dev mode: the repository root, so `python main.py` keeps
      writing into the checkout exactly as before (`generated/`, the demo
      assignments file, etc.) -- no behavior change for developers.
    - PyInstaller mode: a per-user app-data directory outside the bundled,
      potentially read-only installation folder, so the app never tries to
      write next to (or inside) the .exe.
    """
    if is_frozen():
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        root = Path(base) / APP_NAME
        root.mkdir(parents=True, exist_ok=True)
        return root
    return get_resource_root()


def ensure_writable_directories(writable_root: Path) -> None:
    """Create the writable directory layout expected by the app, if missing."""
    (writable_root / "generated" / "runtime_liveries").mkdir(parents=True, exist_ok=True)
    (writable_root / "config" / "models" / "f2002").mkdir(parents=True, exist_ok=True)
    (writable_root / "logs").mkdir(parents=True, exist_ok=True)


def ensure_seeded_writable_file(resource_root: Path, writable_root: Path, relative_path: Path) -> Path:
    """Return the writable path for a file, seeding it from the bundled default once.

    Never edits the bundled copy under `resource_root`; only copies it to the
    writable location the first time no writable copy exists yet.
    """
    writable_path = writable_root / relative_path
    writable_path.parent.mkdir(parents=True, exist_ok=True)
    if not writable_path.exists():
        bundled_path = resource_root / relative_path
        if bundled_path.is_file():
            shutil.copyfile(bundled_path, writable_path)
    return writable_path


def get_seeded_writable_paths(resource_root: Path, writable_root: Path) -> dict[Path, Path]:
    """Seed every known writable-but-defaulted file and return relative->writable map."""
    ensure_writable_directories(writable_root)
    return {
        relative: ensure_seeded_writable_file(resource_root, writable_root, relative)
        for relative in _SEEDED_WRITABLE_FILES
    }

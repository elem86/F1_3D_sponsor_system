"""Custom PyInstaller hook for Panda3D.

`pyinstaller-hooks-contrib` ships no Panda3D hook (verified before writing
this one), so PyInstaller's default analysis only picks up the top-level
`panda3d.core`/`direct.*` Python modules it can see imported directly. Left
alone, the frozen build is missing:

  - the compiled extension modules for every Panda3D sub-namespace
    (panda3d.core, panda3d.direct, panda3d.physics, ...) since they are
    C extensions loaded dynamically, not plain imports PyInstaller can trace
  - every DLL Panda3D depends on at runtime: the OpenGL renderer
    (libpandagl.dll), the Windows display/window backend
    (libp3windisplay.dll), the GLB/glTF model loader
    (libp3ptloader.dll + libp3assimp.dll), audio backends, etc.
  - `panda3d/etc/*.prc` -- Config.prc/Confauto.prc define default window,
    renderer-search-order, and plugin-loading behavior; without them Panda3D
    falls back to hardcoded internal defaults that may not include the
    Windows/OpenGL pipeline this app relies on
  - `panda3d/models/` -- Panda's built-in default font and GUI assets that
    DirectGUI (DirectLabel/DirectButton/etc.) can fall back to internally

This hook collects all of the above explicitly so a onedir build launches,
opens a real window, loads the GLB, and renders DirectGUI without relying on
PyInstaller's static import analysis to have found them on its own.
"""

from __future__ import annotations

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# All C-extension submodules under the panda3d namespace package (core,
# direct, physics, ai, bullet, ...) plus every direct.* Python submodule
# (showbase/gui/task/etc.) that DirectGUI and ShowBase pull in internally.
hiddenimports = (
    collect_submodules("panda3d")
    + collect_submodules("direct")
    + [
        "panda3d.core",
        "panda3d.direct",
    ]
)

# etc/*.prc (default engine configuration) and models/ (built-in fonts/GUI
# assets) must ship as data next to the collected panda3d package, not be
# silently dropped as "non-Python resources".
datas = collect_data_files("panda3d", include_py_files=False)


def _panda3d_root() -> str:
    import panda3d

    return os.path.dirname(panda3d.__file__)


# Every DLL/PYD in the panda3d package directory: PyInstaller's default
# binary scan can miss ones that are loaded dynamically at runtime (plugins
# selected via Config.prc) rather than linked directly by an imported .pyd.
binaries = []
_root = _panda3d_root()
for _name in os.listdir(_root):
    _lower = _name.lower()
    if _lower.endswith((".dll", ".pyd")):
        binaries.append((os.path.join(_root, _name), "panda3d"))

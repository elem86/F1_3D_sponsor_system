# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the F1 3D Sponsor System.

Usage:
    pyinstaller F1SponsorSystem.spec

Produces a onedir build at dist/F1SponsorSystem/F1SponsorSystem.exe.

Set the environment variable F1SPONSOR_DEBUG_CONSOLE=1 before running
PyInstaller to build a console-enabled debug variant instead of the normal
windowed release build (see build_exe.bat for the two prebuilt invocations).
"""

from __future__ import annotations

import os

PROJECT_ROOT = os.path.abspath(os.path.dirname(SPEC))

DEBUG_CONSOLE = os.environ.get("F1SPONSOR_DEBUG_CONSOLE", "") == "1"

block_cipher = None

# -- Bundled read-only application data --------------------------------------
# Every runtime-loaded config/asset the audit identified, and nothing else:
# no Blender authoring files, no raw/legacy slot data, no unused fictional
# logos, no debug/reference material. (source, destination-folder-in-bundle)
datas = [
    ("assets/models/f2002/f2002.glb", "assets/models/f2002"),
    ("assets/models/f2002/white_base.png", "assets/models/f2002"),
    ("assets/models/f2002/no_branding.png", "assets/models/f2002"),
    ("assets/models/f2002/uvmap.png", "assets/models/f2002"),
    ("assets/logos/veltrix.png", "assets/logos"),
    ("assets/logos/nordyn.png", "assets/logos"),
    ("assets/logos/kinetra.png", "assets/logos"),
    ("assets/logos/orbix.png", "assets/logos"),
    ("assets/logos/aeron.png", "assets/logos"),
    ("assets/logos/zentra.png", "assets/logos"),
    ("assets/branding/default_team/aeron_wordmark.png", "assets/branding/default_team"),
    ("assets/branding/default_team/aeron_small.png", "assets/branding/default_team"),
    ("assets/branding/default_team/number_1.png", "assets/branding/default_team"),
    ("config/models/f2002/model.json", "config/models/f2002"),
    ("config/models/f2002/sponsor_slots.json", "config/models/f2002"),
    ("config/models/f2002/demo_assignments.json", "config/models/f2002"),
    ("config/sponsors.json", "config"),
    ("config/sponsor_values.json", "config"),
    ("config/teams/default_team.json", "config/teams"),
]

hiddenimports = [
    "PIL._tkinter_finder",
]

a = Analysis(
    ["main.py"],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[os.path.join(PROJECT_ROOT, "pyinstaller_hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "numpy.testing",
        # Panda3D/direct optionally integrate with an interactive Python
        # shell for live debugging; collect_submodules("direct") transitively
        # imports that integration and drags in whatever interactive-shell
        # stack happens to be installed in the *build* environment. None of
        # it is used by this app's runtime UI, so it is excluded to keep the
        # distribution to what main.py actually needs.
        "IPython",
        "jedi",
        "parso",
        "zmq",
        "tornado",
        "psutil",
        "prompt_toolkit",
        "pygments",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="F1SponsorSystem",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=DEBUG_CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, "assets", "branding", "app_icon.ico")
    if os.path.isfile(os.path.join(PROJECT_ROOT, "assets", "branding", "app_icon.ico"))
    else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="F1SponsorSystem",
)

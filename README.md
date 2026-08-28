# F1 3D Sponsor System

This Panda3D project displays a free F2002-style GLB, generates a clean custom
2024×2024 livery, and provides a runtime sponsor assignment editor. Sponsor
slots are authored externally in Blender. The original GLB hierarchy and all
child transforms remain intact.

## Run

Activate the repository virtual environment, then start the runtime sponsor
viewer:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

The runtime accepts an empty slot configuration. Once Blender-authored slots
exist, its dropdowns are populated from the F2002 slot file and the shared
fictional sponsor catalog; no slot names are hard-coded in the viewer.

Controls: left-drag orbits, the mouse wheel zooms, `R` resets the camera, and
`Esc` quits.

## Define sponsor slots

Create and calibrate F2002 sponsor slots manually in Blender. Preserve the full
export as `config/models/f2002/sponsor_slots_raw.json`, then compile the compact
runtime file with:

```powershell
python scripts/build_f2002_slots.py
```

The Panda3D application reads `config/models/f2002/sponsor_slots.json` and does
not create, select, or modify slot geometry. The three nose slots additionally
define normalized sponsor and reserved team-branding sub-areas.

## Team branding and diagnostics

The active identity is configured in `config/teams/default_team.json`. Built-in
wordmark and small-mark painting is disabled by default. The separately
configurable driver number remains enabled. These transparent assets can be
regenerated with:

```powershell
python scripts/generate_team_branding.py
```

Generate an all-slot orientation texture and a real-logo example with:

```powershell
python scripts/generate_f2002_diagnostic_livery.py
```

Every output starts from `white_base.png`, places only enabled overlays, and then
places the complete current sponsor assignment map. Previous generated liveries
are never used as source images. F2002 sponsor pixels are fitted and clipped by
the union of Blender-selected face polygons, not by rectangular bounds alone.

## Model-specific files

- `config/models/f2002/model.json` — source assets, texture size, root orientation,
  and inspected node-role notes.
- `config/models/f2002/sponsor_slots_raw.json` — untouched Blender extraction.
- `config/models/f2002/sponsor_slots.json` — compact compiled runtime slots.
- `config/models/f2002/demo_assignments.json` — current F2002 runtime assignments.
- `config/teams/default_team.json` — AERON identity and driver number.
- `assets/models/f2002/white_base.png` — plain white, opaque production base.
- `assets/models/f2002/no_branding.png` — untouched source reference texture.
- `assets/models/f2002/uvmap.png` — untouched UV reference texture.
- `generated/f2002_team_livery.png` — deterministic generated RGB atlas.
- `generated/f2002_slot_diagnostic.png` — all-slot orientation diagnostic.
- `generated/f2002_example_livery.png` — driver-number and sponsor example.
- `generated/debug/f2002_masks/` — per-slot raw/effective mask previews.

Root-level slot and assignment files belong to the previous model and are kept
only as legacy reference data. The F2002 tools never load them.

## Building a Windows executable

The app can be packaged into a standalone Windows build with PyInstaller so
another user can run it without installing Python. The bundled resources
(model, textures, logos, config) are read-only; anything the app writes at
runtime (the generated livery, saved sponsor assignments) goes to a separate
writable app-data directory instead, so the packaged app never needs to write
inside its own install folder.

1. Create and activate a virtual environment.
2. Install runtime requirements: `pip install -r requirements.txt`
3. Install build requirements: `pip install -r requirements-build.txt`
4. Run the build script:
   ```powershell
   build_exe.bat
   ```
   or, for a console-enabled debug variant (useful for diagnosing startup
   issues, since the normal build has no console window):
   ```powershell
   build_exe.bat debug
   ```
5. The finished onedir build is written to:
   ```
   dist\F1SponsorSystem\F1SponsorSystem.exe
   ```
   Everything under `dist\F1SponsorSystem\` is required; it is a
   self-contained folder that can be copied or zipped as-is.

The build is driven by the versioned `F1SponsorSystem.spec` file (which lists
every bundled data file explicitly) plus a custom PyInstaller hook in
`pyinstaller_hooks/hook-panda3d.py`, since Panda3D ships no hook of its own in
`pyinstaller-hooks-contrib`. That hook collects Panda3D's compiled extension
modules, its renderer/display-backend/GLB-loader DLLs, and its `etc/*.prc`
default-configuration and `models/` built-in-asset directories, none of which
PyInstaller's static import analysis can discover on its own.

### Resource root vs. writable root

`livery/app_paths.py` is the single place that decides where the app reads
bundled files from and where it writes runtime output to, so the rest of the
codebase never hard-codes a path relative to `python main.py`'s working
directory. It exposes two roots:

- **Resource root** (`get_resource_root()`) — read-only. In source/dev mode
  this is the repository root; in a packaged build it is PyInstaller's
  extracted bundle directory (`sys._MEIPASS`). The model, textures, logos,
  and shipped config JSON are always read from here and are never modified
  by the running app.
- **Writable root** (`get_writable_root()`) — read/write. In source/dev mode
  this is also the repository root, so `python main.py` behaves exactly as
  it did before packaging existed. In a packaged build it is
  `%LOCALAPPDATA%\F1SponsorSystem\`, since the install folder itself may be
  read-only or shared across users. The generated livery
  (`generated/f2002_team_livery.png`), runtime texture revisions
  (`generated/runtime_liveries/`), and the live sponsor assignments
  (`config/models/f2002/demo_assignments.json`) all live under this root.

The assignments file is also *seeded*: the first time the app runs with no
writable copy yet, `get_seeded_writable_paths()` copies the bundled default
into the writable root once, and every later read/write (including Save
Layout) targets only that writable copy. The bundled copy under the resource
root is never edited in place, so reinstalling or re-extracting the app
never clobbers a saved sponsor layout, and a corrupted writable copy can
always be discarded to fall back to the shipped default.

### Running the prebuilt version

If you received a prebuilt copy instead of building it yourself, unzip it (if
zipped) and run:

```
F1SponsorSystem.exe
```

from inside the `F1SponsorSystem` folder. No Python installation is required.
On first launch the app creates a writable data folder at
`%LOCALAPPDATA%\F1SponsorSystem\` (generated livery output and your saved
sponsor layout live there); the bundled install folder itself is never
modified.

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

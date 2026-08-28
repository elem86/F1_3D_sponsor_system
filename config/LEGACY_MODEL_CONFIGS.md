# Legacy model configuration

The root-level `sponsor_slots.json`, `demo_assignments.json`, and diagnostic
slot-calibration files describe the previous car model. They are retained as
reference data only and must not be loaded by the F2002 runtime.

F2002-specific model metadata, assignments, and externally authored slots live in
`config/models/f2002/`. No UV coordinates or face indices from the legacy model
have been copied into that directory.

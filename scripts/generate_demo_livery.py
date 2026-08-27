from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from livery.config_loader import load_json
from livery.base_generator import generate_team_base
from livery.generator import LiveryGenerator


TEAM_PATH = PROJECT_ROOT / "config" / "demo_team.json"
SLOTS_PATH = PROJECT_ROOT / "config" / "sponsor_slots.json"
SPONSORS_PATH = PROJECT_ROOT / "config" / "sponsors.json"
ASSIGNMENTS_PATH = PROJECT_ROOT / "config" / "demo_assignments.json"
BASE_OUTPUT_PATH = PROJECT_ROOT / "generated" / "demo_team_base.png"
FINAL_OUTPUT_PATH = PROJECT_ROOT / "generated" / "demo_sponsor_livery_hq.png"


def main() -> None:
    team = load_json(TEAM_PATH)
    slots = load_json(SLOTS_PATH)
    sponsors = load_json(SPONSORS_PATH)
    assignments = load_json(ASSIGNMENTS_PATH)

    unknown_slots = sorted(set(assignments) - set(slots))
    unknown_sponsors = sorted(set(assignments.values()) - set(sponsors))
    if unknown_slots:
        raise KeyError(f"Assignments contain unknown slots: {', '.join(unknown_slots)}")
    if unknown_sponsors:
        raise KeyError(
            f"Assignments contain unknown sponsors: {', '.join(unknown_sponsors)}"
        )

    base_path = generate_team_base(team, BASE_OUTPUT_PATH)
    generator = LiveryGenerator(base_path, slots)
    final_path = generator.generate(assignments, sponsors, FINAL_OUTPUT_PATH)

    print(f"Team name: {team['name']}")
    print(f"Base color: {team['colors']['primary']}")
    print(f"Output base texture: {base_path}")
    print(f"Output final texture: {final_path}")
    print(f"Sponsors placed: {len(assignments)}")


if __name__ == "__main__":
    main()

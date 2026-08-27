from __future__ import annotations

from typing import Dict, Any, List


class SponsorAssignmentEngine:
    """
    Assign sponsors to slots automatically based on sponsor preferences
    and slot availability.

    This is a simple prototype. Later you can make it much smarter.
    """

    def __init__(self, sponsor_data: Dict[str, Any], available_slots: List[str]):
        self.sponsor_data = sponsor_data
        self.available_slots = available_slots

    def auto_assign(self, sponsor_names: List[str]) -> Dict[str, str]:
        """
        Automatically assign sponsors to slots.

        Sponsors are sorted by importance descending, then assigned to their
        first available preferred slot. If none are available, they are placed
        in any free slot.

        Parameters
        ----------
        sponsor_names : list[str]
            List of sponsor names to place.

        Returns
        -------
        dict
            Maps slot_name -> sponsor_name
        """
        assignments: Dict[str, str] = {}
        free_slots = set(self.available_slots)

        # Sort by importance descending
        sorted_sponsors = sorted(
            sponsor_names,
            key=lambda name: self.sponsor_data[name].get("importance", 0),
            reverse=True,
        )

        for sponsor_name in sorted_sponsors:
            sponsor_info = self.sponsor_data[sponsor_name]
            preferred_slots = sponsor_info.get("preferred_slots", [])

            chosen_slot = None

            # Try preferred slots first
            for slot in preferred_slots:
                if slot in free_slots:
                    chosen_slot = slot
                    break

            # Fallback: use any free slot
            if chosen_slot is None and free_slots:
                chosen_slot = sorted(free_slots)[0]

            if chosen_slot is not None:
                assignments[chosen_slot] = sponsor_name
                free_slots.remove(chosen_slot)

        return assignments

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from livery.config_loader import load_json


def load_tier_values(path: str | Path) -> dict[str, int]:
    """Load the central A/B/C USD value table.

    Represents the commercial/exposure value of one physical sponsor
    position of that tier -- not a sponsor contract, payment, or income.
    """
    data = load_json(path)
    if not isinstance(data, dict) or not data:
        raise ValueError(f"Sponsor value config must be a non-empty JSON object: {path}")
    values: dict[str, int] = {}
    for tier, value in data.items():
        if not isinstance(tier, str) or not tier:
            raise ValueError(f"Sponsor value config keys must be non-empty tier strings: {path}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Sponsor value for tier {tier!r} must be numeric: {path}")
        if value < 0:
            raise ValueError(f"Sponsor value for tier {tier!r} must not be negative: {path}")
        values[tier] = int(value)
    return values


def format_usd(amount: int) -> str:
    """Format a whole-dollar amount as e.g. 350000 -> '$350,000'."""
    return f"${amount:,}"


def slot_value(slot: Mapping[str, Any], tier_values: Mapping[str, int]) -> int | None:
    """Return the configured USD value for one slot's tier, or None if unknown."""
    tier = slot.get("tier") if isinstance(slot, Mapping) else None
    if tier is None:
        return None
    return tier_values.get(tier)


def total_car_value(slots: Mapping[str, Any], tier_values: Mapping[str, int]) -> int:
    """Sum the configured tier value of every sponsor slot on the car."""
    total = 0
    for slot in slots.values():
        value = slot_value(slot, tier_values)
        if value is not None:
            total += value
    return total


def assigned_value(
    slots: Mapping[str, Any],
    assignments: Mapping[str, str],
    tier_values: Mapping[str, int],
) -> int:
    """Sum the tier value of every slot that currently has a sponsor assigned.

    Only real sponsor-slot assignments count -- driver number, team
    branding, and other built-in livery graphics are not sponsor slots and
    are never part of `assignments`, so they are naturally excluded.
    """
    total = 0
    for slot_name, sponsor_id in assignments.items():
        if not sponsor_id:
            continue
        slot = slots.get(slot_name)
        if slot is None:
            continue
        value = slot_value(slot, tier_values)
        if value is not None:
            total += value
    return total


def sponsor_allocated_value(
    sponsor_id: str,
    slots: Mapping[str, Any],
    assignments: Mapping[str, str],
    tier_values: Mapping[str, int],
) -> int:
    """Sum the tier value of every slot currently occupied by one sponsor.

    This is the sponsor's ALLOCATED EXPOSURE -- the advertising/exposure
    value of the car positions it currently occupies. It is unrelated to
    the sponsor's own contract payment; see `get_sponsor_contract_value`.
    """
    total = 0
    for slot_name, assigned_sponsor_id in assignments.items():
        if assigned_sponsor_id != sponsor_id:
            continue
        slot = slots.get(slot_name)
        if slot is None:
            continue
        value = slot_value(slot, tier_values)
        if value is not None:
            total += value
    return total


# -- Sponsor financial layer (contract value / required exposure) -----------
#
# This is a second, independent financial concept from the slot/tier exposure
# values above:
#   - slot/tier value  -> advertising exposure worth of a car POSITION
#   - contract value   -> what the sponsor PAYS the team (income)
#   - required exposure -> the minimum allocated exposure the sponsor expects
#     in return for that payment (a MINIMUM, not an exact target)
#
# There is no negotiation/acceptance logic here: sponsors may always be
# placed anywhere; these functions only report whether a placement already
# satisfies a sponsor's stated requirement.


def get_sponsor_contract_value(sponsor: Mapping[str, Any]) -> int:
    """Return a sponsor's contract payment to the team, or 0 if unset."""
    value = sponsor.get("contract_value_usd", 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def get_sponsor_required_exposure(sponsor: Mapping[str, Any]) -> int:
    """Return a sponsor's minimum required allocated exposure, or 0 if unset."""
    value = sponsor.get("required_exposure_usd", 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def get_slot_value(slot_name: str, slots: Mapping[str, Any], tier_values: Mapping[str, int]) -> int | None:
    """Return the configured USD exposure value for one named slot."""
    slot = slots.get(slot_name)
    if slot is None:
        return None
    return slot_value(slot, tier_values)


def get_sponsor_allocated_exposure(
    sponsor_id: str,
    slots: Mapping[str, Any],
    assignments: Mapping[str, str],
    tier_values: Mapping[str, int],
) -> int:
    """Alias of `sponsor_allocated_value` under the exposure-specific name."""
    return sponsor_allocated_value(sponsor_id, slots, assignments, tier_values)


def is_exposure_requirement_met(
    sponsor_id: str,
    sponsors: Mapping[str, Any],
    slots: Mapping[str, Any],
    assignments: Mapping[str, str],
    tier_values: Mapping[str, int],
) -> bool:
    """A sponsor's requirement is met once allocated exposure >= its minimum.

    Exceeding the requirement is valid; no exact match is required.
    """
    sponsor = sponsors.get(sponsor_id)
    if sponsor is None:
        return False
    required = get_sponsor_required_exposure(sponsor)
    allocated = sponsor_allocated_value(sponsor_id, slots, assignments, tier_values)
    return allocated >= required


def get_active_sponsors(assignments: Mapping[str, str]) -> set[str]:
    """Return the set of sponsor ids currently occupying at least one slot."""
    return {sponsor_id for sponsor_id in assignments.values() if sponsor_id}


def get_total_contract_value(
    assignments: Mapping[str, str], sponsors: Mapping[str, Any]
) -> int:
    """Sum each active sponsor's contract value exactly once, not per slot."""
    total = 0
    for sponsor_id in get_active_sponsors(assignments):
        sponsor = sponsors.get(sponsor_id)
        if sponsor is not None:
            total += get_sponsor_contract_value(sponsor)
    return total


def get_satisfied_contract_value(
    slots: Mapping[str, Any],
    assignments: Mapping[str, str],
    sponsors: Mapping[str, Any],
    tier_values: Mapping[str, int],
) -> int:
    """Sum the contract value of active sponsors whose requirement is met."""
    total = 0
    for sponsor_id in get_active_sponsors(assignments):
        sponsor = sponsors.get(sponsor_id)
        if sponsor is None:
            continue
        if is_exposure_requirement_met(sponsor_id, sponsors, slots, assignments, tier_values):
            total += get_sponsor_contract_value(sponsor)
    return total


def format_usd_millions(amount: int) -> str:
    """Format a whole-dollar amount as compact millions, e.g. 4200000 -> '$4.20M'.

    Intended only for space-constrained sponsor cards; detailed panels must
    keep using `format_usd` for full precision.
    """
    return f"${amount / 1_000_000:.2f}M"

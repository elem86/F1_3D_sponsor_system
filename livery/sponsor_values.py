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
    """Sum the tier value of every slot currently occupied by one sponsor."""
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

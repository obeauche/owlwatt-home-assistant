"""Voice/HomeKit copy-safety tests (Phase 7).

Verifies that entity friendly_names and translation entity strings do NOT
contain forbidden phrases per 06-marketing-copy-canonical.md §4 hard-rules
and 04-legal-implications-for-design.md §C1/C2/C3.

Forbidden phrases (from §4):
  "payout", "OwlWatt pays", "OwlWatt guarantee", "covered", "compensated",
  "refund", "what you're owed by law", "you're entitled to"

Additional forbidden phrases from §C2 (no scalar claim value as state):
  "what you're owed", "you are owed"

Any match in a friendly_name or translation entity name causes test failure.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

COMPONENT_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "custom_components"
    / "owlwatt"
)

# Forbidden phrases from §4 hard-rules + §C2
VOICE_FORBIDDEN_PHRASES = [
    "payout",
    "OwlWatt pays",
    "OwlWatt guarantee",
    "covered",
    "compensated",
    "refund",
    "what you're owed by law",
    "you're entitled to",
    "what you're owed",
    "you are owed",
    "what you are owed",
]


def _all_entity_names_from_const() -> list[str]:
    """Return all friendly_name values from const.py dicts."""
    from custom_components.owlwatt.const import (
        SENSOR_FRIENDLY_NAMES,
        BINARY_SENSOR_FRIENDLY_NAMES,
    )
    return list(SENSOR_FRIENDLY_NAMES.values()) + list(BINARY_SENSOR_FRIENDLY_NAMES.values())


def _all_entity_names_from_translations() -> list[tuple[str, str]]:
    """Return (path, name) pairs from all translation JSON entity sections."""
    results = []
    for json_path in COMPONENT_DIR.rglob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        entity_section = data.get("entity", {})
        for platform, entities in entity_section.items():
            if isinstance(entities, dict):
                for key, val in entities.items():
                    if isinstance(val, dict) and "name" in val:
                        results.append((f"{json_path.name}:entity.{platform}.{key}", val["name"]))
    return results


def test_sensor_friendly_names_no_forbidden_phrases():
    """SENSOR_FRIENDLY_NAMES and BINARY_SENSOR_FRIENDLY_NAMES contain no forbidden phrases."""
    names = _all_entity_names_from_const()
    violations = []
    for name in names:
        for phrase in VOICE_FORBIDDEN_PHRASES:
            if phrase.lower() in name.lower():
                violations.append(f"const.py friendly_name={name!r} contains {phrase!r}")
    assert not violations, "Forbidden phrases in entity friendly_names:\n" + "\n".join(violations)


def test_translation_entity_names_no_forbidden_phrases():
    """Translation entity name strings contain no forbidden phrases."""
    entries = _all_entity_names_from_translations()
    violations = []
    for location, name in entries:
        for phrase in VOICE_FORBIDDEN_PHRASES:
            if phrase.lower() in name.lower():
                violations.append(f"{location}={name!r} contains {phrase!r}")
    assert not violations, "Forbidden phrases in translation entity names:\n" + "\n".join(violations)


def test_translation_entity_names_match_const():
    """Every entity name in translations/en.json matches the value in const.py."""
    from custom_components.owlwatt.const import (
        SENSOR_FRIENDLY_NAMES,
        BINARY_SENSOR_FRIENDLY_NAMES,
    )

    en_json_path = COMPONENT_DIR / "translations" / "en.json"
    data = json.loads(en_json_path.read_text(encoding="utf-8"))
    entity_section = data.get("entity", {})

    mismatches = []

    sensor_entries = entity_section.get("sensor", {})
    for key, val in sensor_entries.items():
        if not isinstance(val, dict):
            continue
        json_name = val.get("name", "")
        const_name = SENSOR_FRIENDLY_NAMES.get(key, "")
        if json_name != const_name:
            mismatches.append(
                f"sensor.{key}: translations={json_name!r} vs const={const_name!r}"
            )

    binary_entries = entity_section.get("binary_sensor", {})
    for key, val in binary_entries.items():
        if not isinstance(val, dict):
            continue
        json_name = val.get("name", "")
        const_name = BINARY_SENSOR_FRIENDLY_NAMES.get(key, "")
        if json_name != const_name:
            mismatches.append(
                f"binary_sensor.{key}: translations={json_name!r} vs const={const_name!r}"
            )

    assert not mismatches, (
        "Translation entity names diverge from const.py:\n" + "\n".join(mismatches)
    )


def test_strings_json_entity_names_match_translations():
    """strings.json entity names match translations/en.json (they should be identical)."""
    en_path = COMPONENT_DIR / "translations" / "en.json"
    strings_path = COMPONENT_DIR / "strings.json"

    en_data = json.loads(en_path.read_text(encoding="utf-8"))
    strings_data = json.loads(strings_path.read_text(encoding="utf-8"))

    en_entities = en_data.get("entity", {})
    strings_entities = strings_data.get("entity", {})

    mismatches = []
    for platform, entries in en_entities.items():
        if not isinstance(entries, dict):
            continue
        for key, val in entries.items():
            if not isinstance(val, dict):
                continue
            en_name = val.get("name", "")
            strings_name = (
                strings_entities.get(platform, {}).get(key, {}).get("name", "MISSING")
            )
            if en_name != strings_name:
                mismatches.append(
                    f"{platform}.{key}: en.json={en_name!r} vs strings.json={strings_name!r}"
                )

    assert not mismatches, (
        "strings.json entity names diverge from translations/en.json:\n"
        + "\n".join(mismatches)
    )


def test_no_scalar_claim_value_entity_name():
    """No entity name implies a single precise dollar amount (C2 compliance).

    'Documented shortfall value' is OK (it's the display_text sensor — the
    STATE itself is a range string like '$308 – $411').
    'Documented shortfall value (low)' and '(high)' are OK — range endpoints.
    Any name that reads as a scalar owed amount is forbidden.
    """
    names = _all_entity_names_from_const()
    # The scalar-owed framing we want to prevent:
    scalar_patterns = [
        "what you're owed",
        "money owed",
        "claim payout",
        "claim value usd",  # entity ID as name (old anti-pattern)
    ]
    violations = []
    for name in names:
        for pattern in scalar_patterns:
            if pattern.lower() in name.lower():
                violations.append(f"friendly_name={name!r} has scalar-owed framing {pattern!r}")
    assert not violations, "Scalar claim-value entity names found:\n" + "\n".join(violations)

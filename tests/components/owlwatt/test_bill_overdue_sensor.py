"""Tests for OwlWattBillOverdueBinarySensor.

Verifies that is_on follows the bill_status.state field in the snapshot
and that extra_state_attributes are populated correctly.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.owlwatt.binary_sensor import OwlWattBillOverdueBinarySensor

from .conftest import TRIAL_SNAPSHOT, PAID_SNAPSHOT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_coordinator(snapshot: dict):
    coordinator = MagicMock()
    coordinator.data = snapshot
    coordinator.last_update_success = True
    return coordinator


def _mock_entry(entry_id: str = "test-entry"):
    entry = MagicMock()
    entry.entry_id = entry_id
    return entry


def _make_sensor(snapshot: dict) -> OwlWattBillOverdueBinarySensor:
    coordinator = _mock_coordinator(snapshot)
    entry = _mock_entry()
    return OwlWattBillOverdueBinarySensor(coordinator, entry)


# ---------------------------------------------------------------------------
# Tests: state follows bill_status.state
# ---------------------------------------------------------------------------

def test_bill_overdue_red_state():
    """is_on is True when state == 'red'."""
    snap = {
        **PAID_SNAPSHOT,
        "bill_status": {
            "cycle_days": 30,
            "next_expected_date": "2026-04-07",
            "overdue_days": 8,
            "state": "red",
        },
    }
    sensor = _make_sensor(snap)
    assert sensor.is_on is True


def test_bill_overdue_amber_state():
    """is_on is False when state == 'amber' (not yet 5 days overdue)."""
    snap = {
        **PAID_SNAPSHOT,
        "bill_status": {
            "cycle_days": 30,
            "next_expected_date": "2026-05-07",
            "overdue_days": 2,
            "state": "amber",
        },
    }
    sensor = _make_sensor(snap)
    assert sensor.is_on is False


def test_bill_overdue_on_time_state():
    """is_on is False when state == 'on_time'."""
    snap = {
        **PAID_SNAPSHOT,
        "bill_status": {
            "cycle_days": 30,
            "next_expected_date": "2026-06-07",
            "overdue_days": 0,
            "state": "on_time",
        },
    }
    sensor = _make_sensor(snap)
    assert sensor.is_on is False


def test_bill_overdue_unknown_state():
    """is_on is False when state == 'unknown' (insufficient bill history)."""
    snap = {
        **TRIAL_SNAPSHOT,
        "bill_status": {
            "cycle_days": None,
            "next_expected_date": None,
            "overdue_days": 0,
            "state": "unknown",
        },
    }
    sensor = _make_sensor(snap)
    assert sensor.is_on is False


def test_bill_overdue_missing_bill_status_field():
    """is_on is None (unknown) when bill_status key is absent (older cloud)."""
    snap = dict(PAID_SNAPSHOT)  # no bill_status key
    sensor = _make_sensor(snap)
    assert sensor.is_on is None


# ---------------------------------------------------------------------------
# Tests: extra_state_attributes
# ---------------------------------------------------------------------------

def test_bill_overdue_attributes_populated():
    """Attributes include cycle_days, next_expected_date, overdue_days, bill_state."""
    snap = {
        **PAID_SNAPSHOT,
        "bill_status": {
            "cycle_days": 30,
            "next_expected_date": "2026-04-07",
            "overdue_days": 8,
            "state": "red",
        },
    }
    sensor = _make_sensor(snap)
    attrs = sensor.extra_state_attributes
    assert attrs["cycle_days"] == 30
    assert attrs["next_expected_date"] == "2026-04-07"
    assert attrs["overdue_days"] == 8
    assert attrs["bill_state"] == "red"


def test_bill_overdue_attributes_partial_when_unknown():
    """Attributes skip None values when bill_status is sparsely populated."""
    snap = {
        **TRIAL_SNAPSHOT,
        "bill_status": {
            "cycle_days": None,
            "next_expected_date": None,
            "overdue_days": 0,
            "state": "unknown",
        },
    }
    sensor = _make_sensor(snap)
    attrs = sensor.extra_state_attributes
    # None fields should not be included
    assert "cycle_days" not in attrs
    assert "next_expected_date" not in attrs
    # overdue_days=0 is not None so it should be present
    assert attrs.get("overdue_days") == 0
    assert attrs.get("bill_state") == "unknown"


def test_bill_overdue_attributes_empty_when_no_bill_status():
    """Attributes are empty when bill_status is absent from snapshot."""
    snap = dict(PAID_SNAPSHOT)
    sensor = _make_sensor(snap)
    assert sensor.extra_state_attributes == {}

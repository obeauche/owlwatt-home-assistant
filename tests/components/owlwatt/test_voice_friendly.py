"""Voice-friendly name tests — assert every sensor/binary_sensor _attr_name
matches the canonical table in 06-marketing-copy-canonical.md §4 exactly.

Source of truth: SENSOR_FRIENDLY_NAMES and BINARY_SENSOR_FRIENDLY_NAMES in
custom_components/owlwatt/const.py, which mirror §4.

Each test instantiates the class (using mock coordinator + entry) and checks
_attr_name directly to guarantee the runtime value is not just a dict lookup
but is actually set on the entity object.
"""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from custom_components.owlwatt.sensor import (
    OwlWattProductionNowSensor,
    OwlWattProductionTodaySensor,
    OwlWattProductionMonthSensor,
    OwlWattExpectedTodaySensor,
    OwlWattExpectedMonthSensor,
    OwlWattShortfallTodayPctSensor,
    OwlWattShortfallMonthPctSensor,
    OwlWattShortfallMonthKwhSensor,
    OwlWattDataFreshnessSensor,
    OwlWattSubscriptionTierSensor,
    OwlWattTrialDaysRemainingSensor,
    OwlWattClaimValueLowSensor,
    OwlWattClaimValueHighSensor,
    OwlWattClaimValueDisplayTextSensor,
    OwlWattClaimStatusSensor,
    OwlWattActiveClaimsCountSensor,
    OwlWattAnomalyLabelSensor,
)
from custom_components.owlwatt.binary_sensor import (
    OwlWattDataStaleSensor,
    OwlWattAnomalyActiveSensor,
)
from .conftest import TRIAL_SNAPSHOT


def _make(cls):
    coordinator = MagicMock()
    coordinator.data = dict(TRIAL_SNAPSHOT)
    coordinator.last_update_success = True
    entry = MagicMock()
    entry.entry_id = "voice-test"
    return cls(coordinator, entry)


# ---------------------------------------------------------------------------
# Sensor friendly names — §4 table (always-on sensors)
# ---------------------------------------------------------------------------

def test_production_now_name():
    assert _make(OwlWattProductionNowSensor)._attr_name == "Solar production right now"


def test_production_today_name():
    assert _make(OwlWattProductionTodaySensor)._attr_name == "Solar production today"


def test_production_month_name():
    assert _make(OwlWattProductionMonthSensor)._attr_name == "Solar production this month"


def test_expected_today_name():
    assert _make(OwlWattExpectedTodaySensor)._attr_name == "Expected solar today"


def test_expected_month_name():
    assert _make(OwlWattExpectedMonthSensor)._attr_name == "Expected solar this month"


def test_shortfall_today_pct_name():
    assert _make(OwlWattShortfallTodayPctSensor)._attr_name == "Solar shortfall today (percent)"


def test_shortfall_month_pct_name():
    assert _make(OwlWattShortfallMonthPctSensor)._attr_name == "Solar shortfall this month (percent)"


def test_shortfall_month_kwh_name():
    assert _make(OwlWattShortfallMonthKwhSensor)._attr_name == "Solar shortfall this month (kWh)"


def test_data_freshness_name():
    assert _make(OwlWattDataFreshnessSensor)._attr_name == "OwlWatt data freshness"


def test_subscription_tier_name():
    assert _make(OwlWattSubscriptionTierSensor)._attr_name == "OwlWatt subscription"


def test_trial_days_remaining_name():
    assert _make(OwlWattTrialDaysRemainingSensor)._attr_name == "OwlWatt trial days remaining"


# ---------------------------------------------------------------------------
# Sensor friendly names — §4 table (paid-tier sensors)
# ---------------------------------------------------------------------------

def test_claim_value_low_name():
    # C2 split: low endpoint of the range
    assert _make(OwlWattClaimValueLowSensor)._attr_name == "Documented shortfall value (low)"


def test_claim_value_high_name():
    # C2 split: high endpoint of the range
    assert _make(OwlWattClaimValueHighSensor)._attr_name == "Documented shortfall value (high)"


def test_claim_value_display_text_name():
    # Maps to §4 row for sensor.owlwatt_claim_value_usd — "Documented shortfall value"
    assert _make(OwlWattClaimValueDisplayTextSensor)._attr_name == "Documented shortfall value"


def test_claim_status_name():
    assert _make(OwlWattClaimStatusSensor)._attr_name == "Claim status"


def test_active_claims_count_name():
    assert _make(OwlWattActiveClaimsCountSensor)._attr_name == "Open claims"


def test_anomaly_label_name():
    assert _make(OwlWattAnomalyLabelSensor)._attr_name == "Anomaly detail"


# ---------------------------------------------------------------------------
# Binary sensor friendly names — §4 table
# ---------------------------------------------------------------------------

def test_data_stale_name():
    assert _make(OwlWattDataStaleSensor)._attr_name == "OwlWatt data is stale"


def test_anomaly_active_name():
    # Voice query: "Is my solar underperforming"
    assert _make(OwlWattAnomalyActiveSensor)._attr_name == "Solar anomaly"


# ---------------------------------------------------------------------------
# Bulk: SENSOR_FRIENDLY_NAMES dict is the canonical registry
# ---------------------------------------------------------------------------

def test_const_matches_all_sensor_keys():
    """Every key in SENSOR_FRIENDLY_NAMES produces a sensor with that exact name."""
    from custom_components.owlwatt.const import SENSOR_FRIENDLY_NAMES

    sensor_classes = [
        OwlWattProductionNowSensor,
        OwlWattProductionTodaySensor,
        OwlWattProductionMonthSensor,
        OwlWattExpectedTodaySensor,
        OwlWattExpectedMonthSensor,
        OwlWattShortfallTodayPctSensor,
        OwlWattShortfallMonthPctSensor,
        OwlWattShortfallMonthKwhSensor,
        OwlWattDataFreshnessSensor,
        OwlWattSubscriptionTierSensor,
        OwlWattTrialDaysRemainingSensor,
        OwlWattClaimValueLowSensor,
        OwlWattClaimValueHighSensor,
        OwlWattClaimValueDisplayTextSensor,
        OwlWattClaimStatusSensor,
        OwlWattActiveClaimsCountSensor,
        OwlWattAnomalyLabelSensor,
    ]
    for cls in sensor_classes:
        sensor = _make(cls)
        key = sensor._key
        expected_name = SENSOR_FRIENDLY_NAMES.get(key)
        assert expected_name is not None, f"Key {key!r} missing from SENSOR_FRIENDLY_NAMES"
        assert sensor._attr_name == expected_name, (
            f"{cls.__name__}._attr_name={sensor._attr_name!r} "
            f"but SENSOR_FRIENDLY_NAMES[{key!r}]={expected_name!r}"
        )


def test_const_matches_all_binary_sensor_keys():
    """Every key in BINARY_SENSOR_FRIENDLY_NAMES produces a binary sensor with that exact name."""
    from custom_components.owlwatt.const import BINARY_SENSOR_FRIENDLY_NAMES

    binary_classes = [
        OwlWattDataStaleSensor,
        OwlWattAnomalyActiveSensor,
    ]
    for cls in binary_classes:
        sensor = _make(cls)
        key = sensor._key
        expected_name = BINARY_SENSOR_FRIENDLY_NAMES.get(key)
        assert expected_name is not None, f"Key {key!r} missing from BINARY_SENSOR_FRIENDLY_NAMES"
        assert sensor._attr_name == expected_name, (
            f"{cls.__name__}._attr_name={sensor._attr_name!r} "
            f"but BINARY_SENSOR_FRIENDLY_NAMES[{key!r}]={expected_name!r}"
        )

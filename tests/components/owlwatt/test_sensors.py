"""Tests for OwlWatt sensor entities.

Covers:
- Trial customer: paid sensors report STATE_UNAVAILABLE + paid_tier_required attr
- Paid customer: range fields are numeric (value_low_usd, value_high_usd)
- method_label == "Independent measurement" in expected attributes
- device_class assignments
- C2 compliance: no scalar value_usd sensor
"""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.owlwatt.sensor import (
    OwlWattProductionNowSensor,
    OwlWattProductionTodaySensor,
    OwlWattProductionMonthSensor,
    OwlWattSolarLifetimeKwhSensor,
    OwlWattExpectedTodaySensor,
    OwlWattExpectedMonthSensor,
    OwlWattShortfallTodayPctSensor,
    OwlWattShortfallMonthPctSensor,
    OwlWattShortfallMonthKwhSensor,
    OwlWattSubscriptionTierSensor,
    OwlWattClaimValueLowSensor,
    OwlWattClaimValueHighSensor,
    OwlWattClaimValueDisplayTextSensor,
    OwlWattClaimStatusSensor,
    OwlWattActiveClaimsCountSensor,
    OwlWattAnomalyLabelSensor,
)
from custom_components.owlwatt.const import MEASUREMENT_DISCLAIMER_SHORT

from .conftest import TRIAL_SNAPSHOT, PAID_SNAPSHOT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_coordinator(snapshot: dict):
    coordinator = MagicMock()
    coordinator.data = snapshot
    coordinator.last_update_success = True
    return coordinator


def _mock_entry(entry_id="test-entry"):
    entry = MagicMock()
    entry.entry_id = entry_id
    return entry


def _make_sensor(cls, snapshot):
    coordinator = _mock_coordinator(snapshot)
    entry = _mock_entry()
    sensor = cls(coordinator, entry)
    return sensor


# ---------------------------------------------------------------------------
# Always-on sensors — trial
# ---------------------------------------------------------------------------

def test_production_now_trial(trial_snapshot):
    sensor = _make_sensor(OwlWattProductionNowSensor, trial_snapshot)
    assert sensor.native_value == 4123.0
    assert sensor.device_class == SensorDeviceClass.POWER


def test_production_today_trial(trial_snapshot):
    sensor = _make_sensor(OwlWattProductionTodaySensor, trial_snapshot)
    assert sensor.native_value == 18.4
    assert sensor.device_class == SensorDeviceClass.ENERGY


def test_expected_today_method_label(trial_snapshot):
    """method_label in expected sensor attributes must be 'Independent measurement'."""
    sensor = _make_sensor(OwlWattExpectedTodaySensor, trial_snapshot)
    attrs = sensor.extra_state_attributes
    assert attrs["method_label"] == "Independent measurement"


def test_expected_month_method_label(paid_snapshot):
    sensor = _make_sensor(OwlWattExpectedMonthSensor, paid_snapshot)
    attrs = sensor.extra_state_attributes
    assert attrs["method_label"] == "Independent measurement"


def test_shortfall_pct_method_label(trial_snapshot):
    sensor = _make_sensor(OwlWattShortfallTodayPctSensor, trial_snapshot)
    attrs = sensor.extra_state_attributes
    assert attrs["method_label"] == "Independent measurement"


def test_subscription_tier_sensor(trial_snapshot):
    sensor = _make_sensor(OwlWattSubscriptionTierSensor, trial_snapshot)
    assert sensor.native_value == "trial"
    assert sensor.device_class == SensorDeviceClass.ENUM


# ---------------------------------------------------------------------------
# Paid-tier sensors — trial customer gets STATE_UNAVAILABLE
# ---------------------------------------------------------------------------

def test_claim_value_low_trial_unavailable(trial_snapshot):
    sensor = _make_sensor(OwlWattClaimValueLowSensor, trial_snapshot)
    assert sensor.native_value == STATE_UNAVAILABLE
    attrs = sensor.extra_state_attributes
    assert attrs.get("paid_tier_required") is True
    assert "unlock_url" in attrs


def test_claim_value_high_trial_unavailable(trial_snapshot):
    sensor = _make_sensor(OwlWattClaimValueHighSensor, trial_snapshot)
    assert sensor.native_value == STATE_UNAVAILABLE
    attrs = sensor.extra_state_attributes
    assert attrs.get("paid_tier_required") is True


def test_claim_value_display_text_trial_unavailable(trial_snapshot):
    sensor = _make_sensor(OwlWattClaimValueDisplayTextSensor, trial_snapshot)
    assert sensor.native_value == STATE_UNAVAILABLE


def test_claim_status_trial_unavailable(trial_snapshot):
    sensor = _make_sensor(OwlWattClaimStatusSensor, trial_snapshot)
    assert sensor.native_value == STATE_UNAVAILABLE


def test_active_claims_count_trial_unavailable(trial_snapshot):
    sensor = _make_sensor(OwlWattActiveClaimsCountSensor, trial_snapshot)
    assert sensor.native_value == STATE_UNAVAILABLE


def test_anomaly_label_trial_unavailable(trial_snapshot):
    sensor = _make_sensor(OwlWattAnomalyLabelSensor, trial_snapshot)
    assert sensor.native_value == STATE_UNAVAILABLE


# ---------------------------------------------------------------------------
# Paid-tier sensors — paid customer gets real values
# ---------------------------------------------------------------------------

def test_claim_value_low_paid(paid_snapshot):
    sensor = _make_sensor(OwlWattClaimValueLowSensor, paid_snapshot)
    val = sensor.native_value
    assert isinstance(val, (int, float))
    assert val == 308.5


def test_claim_value_high_paid(paid_snapshot):
    sensor = _make_sensor(OwlWattClaimValueHighSensor, paid_snapshot)
    val = sensor.native_value
    assert isinstance(val, (int, float))
    assert val == 411.4


def test_claim_value_low_lte_high(paid_snapshot):
    """C2 compliance: low <= high."""
    low_sensor = _make_sensor(OwlWattClaimValueLowSensor, paid_snapshot)
    high_sensor = _make_sensor(OwlWattClaimValueHighSensor, paid_snapshot)
    assert low_sensor.native_value <= high_sensor.native_value


def test_claim_value_display_text_paid(paid_snapshot):
    sensor = _make_sensor(OwlWattClaimValueDisplayTextSensor, paid_snapshot)
    assert sensor.native_value == "$308 – $411"


def test_paid_sensors_have_disclaimer_attribute(paid_snapshot):
    """All paid-tier sensors must include disclaimer in extra_state_attributes."""
    for cls in (
        OwlWattClaimValueLowSensor,
        OwlWattClaimValueHighSensor,
        OwlWattClaimValueDisplayTextSensor,
    ):
        sensor = _make_sensor(cls, paid_snapshot)
        attrs = sensor.extra_state_attributes
        assert "disclaimer" in attrs, f"{cls.__name__} missing disclaimer"
        assert attrs["disclaimer"] == MEASUREMENT_DISCLAIMER_SHORT


# ---------------------------------------------------------------------------
# C2 compliance — no scalar value_usd sensor exists
# ---------------------------------------------------------------------------

def test_no_scalar_value_usd_sensor_class():
    """There must be no sensor class named OwlWattClaimValueUsdSensor."""
    import custom_components.owlwatt.sensor as sensor_module
    assert not hasattr(sensor_module, "OwlWattClaimValueUsdSensor"), (
        "Scalar claim_value_usd sensor class must not exist (C2 compliance)"
    )


# ---------------------------------------------------------------------------
# Method label forbidden terms — no pvlib/PVWatts/Ineichen in any sensor
# ---------------------------------------------------------------------------

def test_method_label_never_pvlib(paid_snapshot):
    """No sensor's method_label should contain pvlib, PVWatts, Ineichen, 30 signals."""
    forbidden = ["pvlib", "PVWatts", "Ineichen", "30 signals", "30 weather signals"]
    sensors_to_check = [
        OwlWattExpectedTodaySensor,
        OwlWattExpectedMonthSensor,
        OwlWattShortfallTodayPctSensor,
        OwlWattShortfallMonthPctSensor,
        OwlWattShortfallMonthKwhSensor,
    ]
    for cls in sensors_to_check:
        sensor = _make_sensor(cls, paid_snapshot)
        attrs = sensor.extra_state_attributes
        method_label = attrs.get("method_label", "")
        for term in forbidden:
            assert term not in method_label, (
                f"{cls.__name__}.method_label contains forbidden term {term!r}: {method_label!r}"
            )


# ---------------------------------------------------------------------------
# Solar lifetime sensor (HA Energy)
# ---------------------------------------------------------------------------

def test_solar_lifetime_native_value(trial_snapshot):
    """Lifetime sensor surfaces solar_lifetime_kwh from the snapshot."""
    from homeassistant.components.sensor import SensorStateClass
    sensor = _make_sensor(OwlWattSolarLifetimeKwhSensor, trial_snapshot)
    assert sensor.native_value == 12345.6
    assert sensor.device_class == SensorDeviceClass.ENERGY
    assert sensor._attr_state_class == SensorStateClass.TOTAL_INCREASING


def test_solar_lifetime_monotonic_guard_rejects_one_regression():
    """A single downward jump returns None (HA → unavailable) without re-anchoring."""
    coord = _mock_coordinator({"solar_lifetime_kwh": 100.0})
    sensor = OwlWattSolarLifetimeKwhSensor(coord, _mock_entry())
    assert sensor.native_value == 100.0   # first read sets the floor
    coord.data = {"solar_lifetime_kwh": 95.0}
    assert sensor.native_value is None    # regression rejected
    coord.data = {"solar_lifetime_kwh": 101.0}
    assert sensor.native_value == 101.0   # recovers when cloud catches back up


def test_solar_lifetime_re_anchors_after_two_consistent_lower_reads():
    """If cloud reports the same lower value twice, accept it as the new floor."""
    coord = _mock_coordinator({"solar_lifetime_kwh": 100.0})
    sensor = OwlWattSolarLifetimeKwhSensor(coord, _mock_entry())
    assert sensor.native_value == 100.0
    coord.data = {"solar_lifetime_kwh": 95.0}
    assert sensor.native_value is None
    coord.data = {"solar_lifetime_kwh": 95.0}
    assert sensor.native_value == 95.0    # re-anchored


def test_solar_lifetime_missing_field_holds_last_value():
    """If a snapshot omits solar_lifetime_kwh, the sensor keeps its last value."""
    coord = _mock_coordinator({"solar_lifetime_kwh": 100.0})
    sensor = OwlWattSolarLifetimeKwhSensor(coord, _mock_entry())
    assert sensor.native_value == 100.0
    coord.data = {}  # field missing
    assert sensor.native_value == 100.0


# ---------------------------------------------------------------------------
# Documented shortfall value — state_class must be TOTAL, not MEASUREMENT
# ---------------------------------------------------------------------------

def test_claim_value_low_state_class_is_total(paid_snapshot):
    """MEASUREMENT + MONETARY is rejected by HA; must be TOTAL."""
    from homeassistant.components.sensor import SensorStateClass
    sensor = _make_sensor(OwlWattClaimValueLowSensor, paid_snapshot)
    assert sensor._attr_state_class == SensorStateClass.TOTAL


def test_claim_value_high_state_class_is_total(paid_snapshot):
    from homeassistant.components.sensor import SensorStateClass
    sensor = _make_sensor(OwlWattClaimValueHighSensor, paid_snapshot)
    assert sensor._attr_state_class == SensorStateClass.TOTAL

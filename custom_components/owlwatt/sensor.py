"""OwlWatt sensor entities.

Always-on sensors (free + paid):
  production_now, production_today, production_month
  expected_today, expected_month
  shortfall_today_pct, shortfall_month_pct, shortfall_month_kwh
  data_freshness, subscription_tier, trial_days_remaining

Paid-tier sensors (STATE_UNAVAILABLE for trial with paid_tier_required attr):
  claim_value_low_usd, claim_value_high_usd, claim_value_display_text
  claim_status, active_claims_count, anomaly_label

Legal compliance:
- No money-disbursement language in entity names or attributes.
- method_label always "Independent measurement".
- C2: claim value as range (low + high), never scalar.
- MEASUREMENT_DISCLAIMER_SHORT on every paid-tier sensor attribute.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MEASUREMENT_DISCLAIMER_SHORT, SENSOR_FRIENDLY_NAMES
from .coordinator import OwlWattCoordinator

log = logging.getLogger(__name__)

_UNLOCK_URL = "https://owlwatt.com/app/dashboard?upsell=ha"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OwlWatt sensor entities from a config entry."""
    coordinator: OwlWattCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = [
        # Always-on
        OwlWattProductionNowSensor(coordinator, entry),
        OwlWattProductionTodaySensor(coordinator, entry),
        OwlWattProductionMonthSensor(coordinator, entry),
        OwlWattExpectedTodaySensor(coordinator, entry),
        OwlWattExpectedMonthSensor(coordinator, entry),
        OwlWattShortfallTodayPctSensor(coordinator, entry),
        OwlWattShortfallMonthPctSensor(coordinator, entry),
        OwlWattShortfallMonthKwhSensor(coordinator, entry),
        OwlWattDataFreshnessSensor(coordinator, entry),
        OwlWattSubscriptionTierSensor(coordinator, entry),
        OwlWattTrialDaysRemainingSensor(coordinator, entry),
        # Paid-tier (unavailable for trial)
        OwlWattClaimValueLowSensor(coordinator, entry),
        OwlWattClaimValueHighSensor(coordinator, entry),
        OwlWattClaimValueDisplayTextSensor(coordinator, entry),
        OwlWattClaimStatusSensor(coordinator, entry),
        OwlWattActiveClaimsCountSensor(coordinator, entry),
        OwlWattAnomalyLabelSensor(coordinator, entry),
    ]
    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class OwlWattBaseSensor(CoordinatorEntity[OwlWattCoordinator], SensorEntity):
    """Base for all OwlWatt sensor entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OwlWattCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = SENSOR_FRIENDLY_NAMES.get(key, key.replace("_", " ").title())
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="OwlWatt",
            manufacturer="OwlWatt",
            model="Solar Monitor",
            configuration_url="https://owlwatt.com/app/dashboard",
        )

    @property
    def _snapshot(self) -> dict:
        return self.coordinator.data or {}


class OwlWattPaidTierSensor(OwlWattBaseSensor):
    """Sensor that returns STATE_UNAVAILABLE for non-paying customers."""

    def _is_paid(self) -> bool:
        tier = self._snapshot.get("tier", "trial")
        return tier in ("monthly", "annual")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self._is_paid():
            return {
                "paid_tier_required": True,
                "unlock_url": _UNLOCK_URL,
            }
        return {"disclaimer": MEASUREMENT_DISCLAIMER_SHORT}


# ---------------------------------------------------------------------------
# Always-on sensors
# ---------------------------------------------------------------------------

class OwlWattProductionNowSensor(OwlWattBaseSensor):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "production_now")

    @property
    def native_value(self) -> Optional[float]:
        return self._snapshot.get("production", {}).get("current_w")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"method_label": "Independent measurement"}


class OwlWattProductionTodaySensor(OwlWattBaseSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "production_today")

    @property
    def native_value(self) -> Optional[float]:
        return self._snapshot.get("production", {}).get("today_kwh")


class OwlWattProductionMonthSensor(OwlWattBaseSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "production_month")

    @property
    def native_value(self) -> Optional[float]:
        return self._snapshot.get("production", {}).get("month_kwh")


class OwlWattExpectedTodaySensor(OwlWattBaseSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "expected_today")

    @property
    def native_value(self) -> Optional[float]:
        return self._snapshot.get("expected", {}).get("today_kwh")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "method_label": self._snapshot.get("expected", {}).get(
                "method_label", "Independent measurement"
            )
        }


class OwlWattExpectedMonthSensor(OwlWattBaseSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "expected_month")

    @property
    def native_value(self) -> Optional[float]:
        return self._snapshot.get("expected", {}).get("month_kwh")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "method_label": self._snapshot.get("expected", {}).get(
                "method_label", "Independent measurement"
            )
        }


class OwlWattShortfallTodayPctSensor(OwlWattBaseSensor):
    _attr_device_class = None
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "shortfall_today_pct")

    @property
    def native_value(self) -> Optional[float]:
        return self._snapshot.get("shortfall", {}).get("today_pct")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"method_label": "Independent measurement"}


class OwlWattShortfallMonthPctSensor(OwlWattBaseSensor):
    _attr_device_class = None
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "shortfall_month_pct")

    @property
    def native_value(self) -> Optional[float]:
        return self._snapshot.get("shortfall", {}).get("month_pct")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"method_label": "Independent measurement"}


class OwlWattShortfallMonthKwhSensor(OwlWattBaseSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "shortfall_month_kwh")

    @property
    def native_value(self) -> Optional[float]:
        return self._snapshot.get("shortfall", {}).get("month_kwh")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"method_label": "Independent measurement"}


class OwlWattDataFreshnessSensor(OwlWattBaseSensor):
    """Seconds since the last cloud data point was received."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "data_freshness")

    @property
    def native_value(self) -> Optional[float]:
        as_of_str = self._snapshot.get("as_of")
        if not as_of_str:
            return None
        try:
            as_of = datetime.fromisoformat(as_of_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return round((now - as_of).total_seconds())
        except (ValueError, TypeError):
            return None


class OwlWattSubscriptionTierSensor(OwlWattBaseSensor):
    """Subscription tier with upsell attributes (cloud-driven A/B)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["trial", "monthly", "annual", "cancelled"]

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "subscription_tier")

    @property
    def native_value(self) -> Optional[str]:
        return self._snapshot.get("tier")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snap = self._snapshot
        claim = snap.get("claim", {})
        tier = snap.get("tier", "trial")
        trial_ends = None
        if tier == "trial":
            system = snap.get("system", {})
            # trial_days_remaining is served by its own sensor; mirror here too
            tier_label = snap.get("tier_label", "")
            import re
            m = re.search(r"Day (\d+) of 30", tier_label)
            if m:
                trial_days_remaining = 30 - int(m.group(1))
            else:
                trial_days_remaining = None
        else:
            trial_days_remaining = None

        attrs: dict[str, Any] = {
            "tier_label": snap.get("tier_label"),
            "trial_days_remaining": trial_days_remaining,
        }
        # Cloud-driven upsell fields (from future snapshot expansion)
        for upsell_key in ("upsell_visible", "upsell_message", "upsell_url"):
            if upsell_key in snap:
                attrs[upsell_key] = snap[upsell_key]
        return attrs


class OwlWattTrialDaysRemainingSensor(OwlWattBaseSensor):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "trial_days_remaining")

    @property
    def native_value(self) -> Optional[int]:
        tier_label = self._snapshot.get("tier_label", "")
        tier = self._snapshot.get("tier", "")
        if tier != "trial":
            return None
        import re
        m = re.search(r"Day (\d+) of 30", tier_label)
        if m:
            return max(0, 30 - int(m.group(1)))
        return None


# ---------------------------------------------------------------------------
# Paid-tier sensors
# ---------------------------------------------------------------------------

class OwlWattClaimValueLowSensor(OwlWattPaidTierSensor):
    """Low end of the documented shortfall range (USD).

    C2-compliant: range endpoint, not scalar.
    """

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "claim_value_low_usd")

    @property
    def native_value(self):
        if not self._is_paid():
            return STATE_UNAVAILABLE
        return self._snapshot.get("claim", {}).get("value_low_usd")


class OwlWattClaimValueHighSensor(OwlWattPaidTierSensor):
    """High end of the documented shortfall range (USD).

    C2-compliant: range endpoint, not scalar.
    """

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "USD"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "claim_value_high_usd")

    @property
    def native_value(self):
        if not self._is_paid():
            return STATE_UNAVAILABLE
        return self._snapshot.get("claim", {}).get("value_high_usd")


class OwlWattClaimValueDisplayTextSensor(OwlWattPaidTierSensor):
    """Human-readable claim value range, e.g. '$308 – $411'."""

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "claim_value_display_text")

    @property
    def native_value(self):
        if not self._is_paid():
            return STATE_UNAVAILABLE
        return self._snapshot.get("claim", {}).get("value_display_text")


class OwlWattClaimStatusSensor(OwlWattPaidTierSensor):
    """Latest open claim status."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        "detected", "drafted", "customer_review", "sent",
        "acknowledged", "in_progress", "resolved", "denied", "escalated",
    ]

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "claim_status")

    @property
    def native_value(self):
        if not self._is_paid():
            return STATE_UNAVAILABLE
        # claim_status comes from the claims list (loaded separately).
        # The snapshot does not include per-claim status; this sensor
        # relies on the coordinator's extended data if available.
        return self._snapshot.get("_claim_status")  # injected by __init__ if claims polled


class OwlWattActiveClaimsCountSensor(OwlWattPaidTierSensor):
    """Number of open (non-resolved) claims."""

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "active_claims_count")

    @property
    def native_value(self):
        if not self._is_paid():
            return STATE_UNAVAILABLE
        return self._snapshot.get("_active_claims_count")  # injected by __init__


class OwlWattAnomalyLabelSensor(OwlWattPaidTierSensor):
    """Human-readable anomaly label (e.g. 'Production below baseline')."""

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "anomaly_label")

    @property
    def native_value(self):
        if not self._is_paid():
            return STATE_UNAVAILABLE
        return self._snapshot.get("anomaly", {}).get("label")

"""OwlWatt binary sensor entities."""
from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BINARY_SENSOR_FRIENDLY_NAMES, DOMAIN
from .coordinator import OwlWattCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OwlWattCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([
        OwlWattDataStaleSensor(coordinator, entry),
        OwlWattAnomalyActiveSensor(coordinator, entry),
        OwlWattBillOverdueBinarySensor(coordinator, entry),
    ])


class OwlWattBaseBinarySensor(CoordinatorEntity[OwlWattCoordinator], BinarySensorEntity):
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
        self._attr_name = BINARY_SENSOR_FRIENDLY_NAMES.get(
            key, key.replace("_", " ").title()
        )
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


class OwlWattDataStaleSensor(OwlWattBaseBinarySensor):
    """True when the cloud data is stale (> 15 min since last reading)."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "data_stale")

    @property
    def is_on(self) -> Optional[bool]:
        return self._snapshot.get("production", {}).get("stale")


class OwlWattAnomalyActiveSensor(OwlWattBaseBinarySensor):
    """True when an active production anomaly is detected."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "anomaly_active")

    @property
    def is_on(self) -> Optional[bool]:
        return self._snapshot.get("anomaly", {}).get("active")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        label = self._snapshot.get("anomaly", {}).get("label")
        return {"label": label} if label else {}


class OwlWattBillOverdueBinarySensor(OwlWattBaseBinarySensor):
    """True when the next expected bill is 5+ days overdue (state == 'red').

    Reads from the ``bill_status`` block added to the HA snapshot in
    cloud/app/routers/ha_integration.py.  Older HA integration versions
    that do not receive this field will stay in state ``None`` (unknown).
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "bill_overdue")

    @property
    def is_on(self) -> Optional[bool]:
        bill_status = self._snapshot.get("bill_status")
        if bill_status is None:
            return None  # snapshot field not present — report unknown
        return bill_status.get("state") == "red"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        bill_status = self._snapshot.get("bill_status") or {}
        attrs: dict[str, Any] = {}
        if bill_status.get("cycle_days") is not None:
            attrs["cycle_days"] = bill_status["cycle_days"]
        if bill_status.get("next_expected_date") is not None:
            attrs["next_expected_date"] = bill_status["next_expected_date"]
        if bill_status.get("overdue_days") is not None:
            attrs["overdue_days"] = bill_status["overdue_days"]
        if bill_status.get("state") is not None:
            attrs["bill_state"] = bill_status["state"]
        return attrs

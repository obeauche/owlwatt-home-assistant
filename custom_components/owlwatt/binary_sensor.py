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

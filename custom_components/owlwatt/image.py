"""OwlWatt image entity — pre-install reference image (paid tier)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OwlWattCoordinator

log = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OwlWattCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([OwlWattRoofBeforeImage(coordinator, entry)])


class OwlWattRoofBeforeImage(CoordinatorEntity[OwlWattCoordinator], ImageEntity):
    """Image entity for the pre-install reference roof photo (paid tier).

    Trial customers: entity is unavailable (paid_tier_required attribute set).
    """

    _attr_has_entity_name = True
    _attr_name = "OwlWatt pre-install roof"
    _attr_content_type = "image/jpeg"

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, coordinator.hass)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_roof_before_image"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="OwlWatt",
            manufacturer="OwlWatt",
            model="Solar Monitor",
            configuration_url="https://owlwatt.com/app/dashboard",
        )
        self._cached_image: Optional[bytes] = None
        self._image_last_updated: Optional[datetime] = None

    @property
    def _snapshot(self) -> dict:
        return self.coordinator.data or {}

    def _is_paid(self) -> bool:
        tier = self._snapshot.get("tier", "trial")
        return tier in ("monthly", "annual")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def image_last_updated(self) -> Optional[datetime]:
        return self._image_last_updated

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self._is_paid():
            return {
                "paid_tier_required": True,
                "unlock_url": "https://owlwatt.com/app/dashboard?upsell=ha",
            }
        return {}

    async def async_image(self) -> Optional[bytes]:
        """Return pre-install roof image bytes (paid tier only)."""
        if not self._is_paid():
            return None
        try:
            client = self.coordinator.api_client
            data = await client.get_roof_before_image_bytes()
            if data:
                self._cached_image = data
                self._image_last_updated = datetime.now(timezone.utc)
            return data
        except Exception as exc:
            log.warning("owlwatt image: failed to fetch before image: %s", exc)
            return self._cached_image  # return stale cache on error

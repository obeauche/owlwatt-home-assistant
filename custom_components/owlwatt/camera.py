"""OwlWatt camera entity — streams the latest baked roof image (paid tier)."""
from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.camera import Camera
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
    async_add_entities([OwlWattRoofCamera(coordinator, entry)])


class OwlWattRoofCamera(CoordinatorEntity[OwlWattCoordinator], Camera):
    """Camera entity serving the latest baked roof image.

    Paid tier: streams roof image from /api/ha/v1/roof/image.
    Trial tier: reports unavailable with paid_tier_required attribute.

    The Bearer token is never exposed to the browser — images are fetched
    server-side by HA's camera proxy.
    """

    _attr_has_entity_name = True
    _attr_name = "OwlWatt roof view"
    _attr_brand = "OwlWatt"

    def __init__(self, coordinator: OwlWattCoordinator, entry: ConfigEntry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_roof_camera"
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

    def _is_paid(self) -> bool:
        tier = self._snapshot.get("tier", "trial")
        return tier in ("monthly", "annual")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self._is_paid():
            return {
                "paid_tier_required": True,
                "unlock_url": "https://owlwatt.com/app/dashboard?upsell=ha",
            }
        roof_image = self._snapshot.get("roof_image", {})
        return {
            "last_baked_at": roof_image.get("last_baked_at"),
        }

    async def async_camera_image(
        self, width: Optional[int] = None, height: Optional[int] = None
    ) -> Optional[bytes]:
        """Return the latest roof image bytes.

        Returns None (unavailable) for trial customers.
        """
        if not self._is_paid():
            return None
        try:
            client = self.coordinator.api_client
            return await client.get_roof_image_bytes()
        except Exception as exc:
            log.warning("owlwatt camera: failed to fetch roof image: %s", exc)
            return None

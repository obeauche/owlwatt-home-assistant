"""OwlWatt button entities — Phase 6: Refer a Friend button."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OwlWattCoordinator

log = logging.getLogger(__name__)

_REFER_BASE_URL = "https://owlwatt.com/refer?from=ha"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OwlWatt button entities from a ConfigEntry."""
    coordinator: OwlWattCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([OwlWattReferFriendButton(coordinator, entry)])


class OwlWattReferFriendButton(CoordinatorEntity[OwlWattCoordinator], ButtonEntity):
    """Button that opens the OwlWatt referral URL in the user's browser.

    On press:
    1. Try to get customer_id from /api/ha/v1/manifest (best-effort).
    2. Build URL: https://owlwatt.com/refer?from=ha[&referrer=<customer_id>]
    3. Emit a persistent notification with a clickable link.
    4. Also call homeassistant.frontend.open_url if available.

    Both steps are fire-and-forget — the button never raises.
    """

    _attr_has_entity_name = True
    _attr_name = "Refer a friend to OwlWatt"
    _attr_icon = "mdi:share-variant"

    def __init__(
        self,
        coordinator: OwlWattCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_refer_friend"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="OwlWatt",
            manufacturer="OwlWatt",
            model="Solar Monitor",
            configuration_url="https://owlwatt.com/app/dashboard",
        )

    async def _get_referral_url(self) -> str:
        """Build the referral URL, appending referrer= if customer_id is available."""
        try:
            manifest = await self.coordinator.api_client.get_manifest()
            customer_id = manifest.get("customer_id")
            if customer_id is not None:
                return f"{_REFER_BASE_URL}&referrer={customer_id}"
        except Exception as exc:
            log.debug("owlwatt: refer button — could not fetch manifest: %s", exc)
        return _REFER_BASE_URL

    async def async_press(self) -> None:
        """Handle button press — open the referral URL in the user's browser."""
        url = await self._get_referral_url()
        log.info("owlwatt: referral button pressed, opening %s", url)

        # Fire persistent notification (visible in HA notification tray).
        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Refer a Friend to OwlWatt",
                    "message": (
                        f"Share your referral link with a friend:\n\n"
                        f"[Open referral page]({url})"
                    ),
                    "notification_id": "owlwatt_referral",
                },
                blocking=False,
            )
        except Exception as exc:
            log.debug("owlwatt: refer button — persistent_notification failed: %s", exc)

        # Open URL in frontend if the service is available.
        try:
            service_registry = self.hass.services
            if service_registry.has_service("homeassistant", "frontend"):
                await service_registry.async_call(
                    "homeassistant",
                    "frontend",
                    {"url": url},
                    blocking=False,
                )
            elif service_registry.has_service("frontend", "open_url"):
                await service_registry.async_call(
                    "frontend",
                    "open_url",
                    {"url": url},
                    blocking=False,
                )
        except Exception as exc:
            log.debug("owlwatt: refer button — frontend open_url failed: %s", exc)

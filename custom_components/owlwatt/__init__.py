"""OwlWatt Home Assistant integration.

Registers the coordinator and platforms:
  sensor, binary_sensor, camera, image, button

Auth: Bearer token (CustomerApiToken, Phase 0) stored in ConfigEntry.data.
Poll: every 5 min via DataUpdateCoordinator.
Heartbeat: on first poll + every 24 h.

Services
--------
owlwatt.refresh           -- force coordinator refresh
owlwatt.create_share_link -- mint 7-day share URL, fire persistent_notification
"""
from __future__ import annotations

import logging

import aiohttp

from homeassistant.components.persistent_notification import (
    async_create as _pn_create,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import OwlWattApiClient
from .const import CONF_API_BASE, CONF_TOKEN, DEFAULT_API_BASE, DOMAIN
from .coordinator import OwlWattCoordinator

log = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "camera", "image", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OwlWatt from a ConfigEntry."""
    token: str = entry.data[CONF_TOKEN]
    api_base: str = entry.data.get(CONF_API_BASE, DEFAULT_API_BASE)

    session = async_get_clientsession(hass)
    api_client = OwlWattApiClient(session, token, api_base)
    coordinator = OwlWattCoordinator(hass, api_client, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ------------------------------------------------------------------
    # owlwatt.refresh
    # ------------------------------------------------------------------
    async def _handle_refresh(call: ServiceCall) -> None:
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh", _handle_refresh)

    # ------------------------------------------------------------------
    # owlwatt.create_share_link
    #
    # Mints a 7-day signed share URL via POST /api/ha/v1/share.
    # The URL renders a public PNG showing production vs expected,
    # status badge, and anonymized geo-label.
    # No financial claim values in the shared image (C2 compliance).
    # Result surfaced via persistent_notification so the customer can
    # copy or share the link from the HA notification center.
    # ------------------------------------------------------------------
    async def _handle_create_share_link(call: ServiceCall) -> None:
        try:
            result = await api_client.create_share_link()
            url = result.get("url", "") if isinstance(result, dict) else ""

            if url:
                message = (
                    "Your OwlWatt share link is ready (valid 7 days):\n\n"
                    + url
                    + "\n\nThe link shows your production vs expected and status. "
                    "Your address is anonymized. Anyone with the link can view it."
                )
            else:
                message = (
                    "OwlWatt share link created. "
                    "Check your OwlWatt dashboard to view it."
                )

            _pn_create(
                hass,
                message=message,
                title="OwlWatt Share Link Created",
                notification_id="owlwatt_share_link",
            )
        except Exception as exc:
            log.error("owlwatt.create_share_link failed: %s", exc)
            _pn_create(
                hass,
                message=(
                    "Could not create OwlWatt share link. "
                    "Check that your API token has ha:read scope and try again."
                ),
                title="OwlWatt Share Link Error",
                notification_id="owlwatt_share_link_error",
            )

    hass.services.async_register(DOMAIN, "create_share_link", _handle_create_share_link)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Remove services if this is the last entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "refresh")
            hass.services.async_remove(DOMAIN, "create_share_link")
    return unloaded

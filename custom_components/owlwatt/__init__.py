"""OwlWatt Home Assistant integration.

Registers the coordinator and platforms:
  sensor, binary_sensor, camera, image, button

Auth: Bearer token (CustomerApiToken, Phase 0) stored in ConfigEntry.data.
Poll: every 5 min via DataUpdateCoordinator.
Heartbeat: on first poll + every 24 h.
"""
from __future__ import annotations

import logging

import aiohttp

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

    # Register owlwatt.refresh service
    async def _handle_refresh(call: ServiceCall) -> None:
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh", _handle_refresh)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Remove service if this is the last entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "refresh")
    return unloaded

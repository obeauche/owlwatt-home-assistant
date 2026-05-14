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
from .const import (
    CONF_API_BASE,
    CONF_CONFIGURE_HA_ENERGY,
    CONF_TOKEN,
    DEFAULT_API_BASE,
    DOMAIN,
)
from .coordinator import OwlWattCoordinator
from .energy_config import async_configure_ha_energy_if_empty

log = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "camera", "image", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OwlWatt from a ConfigEntry."""
    token: str = entry.data[CONF_TOKEN]
    api_base: str = entry.data.get(CONF_API_BASE, DEFAULT_API_BASE)

    # Migration (2026-05-12): early config entries stored api_base as the
    # internal owlwatt-api.fly.dev hostname, which resolves IPv6-only and
    # fails for HA instances on IPv4-only networks. Rewrite stale stored
    # api_bases to the canonical Cloudflare-fronted owlwatt.com URL.
    if "owlwatt-api.fly.dev" in api_base:
        log.info(
            "owlwatt: migrating api_base from %s to %s (Cloudflare dual-stack)",
            api_base, DEFAULT_API_BASE,
        )
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_API_BASE: DEFAULT_API_BASE},
        )
        api_base = DEFAULT_API_BASE

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
    # Optional HA Energy auto-configuration (opt-in via options flow).
    # Idempotent: never clobbers an existing energy_sources config.
    # ------------------------------------------------------------------
    if entry.options.get(CONF_CONFIGURE_HA_ENERGY, False):
        try:
            await async_configure_ha_energy_if_empty(hass, entry)
        except Exception as exc:
            log.warning("owlwatt: HA Energy auto-config skipped: %s", exc)

    # Reload on options change so toggling the HA Energy checkbox takes effect.
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

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


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration so options changes take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


# Note: ``async_get_solar_forecast`` lives in ``energy.py`` (the HA-discovered
# sub-platform module), NOT here. HA Energy's discovery scans every integration
# for a same-named ``energy.py`` module and inspects THAT for the hook —
# functions on __init__.py are not visible to the forecast scanner.


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

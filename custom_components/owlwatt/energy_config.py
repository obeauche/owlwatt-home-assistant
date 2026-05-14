"""Optional HA Energy dashboard auto-configuration.

Customers can opt in (config-flow checkbox or options flow) to have OwlWatt
register itself as their Energy dashboard's Solar source AND solar forecast
provider. We only ever write when ``energy_sources`` is empty — existing
Energy configurations are never modified.

The lifetime sensor's entity_id is resolved through the entity registry so
slug suffixes (e.g. ``_2`` for a second OwlWatt account) don't break the
lookup.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

log = logging.getLogger(__name__)

_LIFETIME_UNIQUE_ID_KEY = "solar_lifetime_kwh"


async def async_configure_ha_energy_if_empty(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Write starter Energy prefs only if the dashboard is unconfigured.

    Returns True if prefs were written, False if skipped (already configured,
    HA Energy unavailable, or lifetime sensor not yet registered).
    """
    # Resolve the lifetime sensor's real entity_id. Imported lazily because the
    # entity_registry helper isn't covered by the minimal HA test stubs.
    from homeassistant.helpers import entity_registry as er

    ent_reg = er.async_get(hass)
    lifetime_unique_id = f"{entry.entry_id}_{_LIFETIME_UNIQUE_ID_KEY}"
    lifetime_entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, lifetime_unique_id
    )
    if lifetime_entity_id is None:
        log.debug(
            "owlwatt: lifetime sensor not yet in registry; skipping Energy config"
        )
        return False

    # Lazy import — energy component may not be loaded on minimal HA installs.
    try:
        from homeassistant.components.energy import data as energy_data
    except ImportError:
        log.debug("owlwatt: homeassistant.components.energy unavailable")
        return False

    try:
        manager = await energy_data.async_get_manager(hass)
    except Exception as exc:
        log.debug("owlwatt: could not get Energy manager: %s", exc)
        return False

    current = manager.data or {}
    existing_sources = current.get("energy_sources") or []
    if existing_sources:
        log.info(
            "owlwatt: Energy dashboard already has %d source(s); skipping",
            len(existing_sources),
        )
        return False

    starter: dict[str, Any] = {
        "currency": (current.get("currency") or hass.config.currency or "USD"),
        "energy_sources": [
            {
                "type": "solar",
                "stat_energy_from": lifetime_entity_id,
                "config_entry_solar_forecast": [entry.entry_id],
            }
        ],
        "device_consumption": current.get("device_consumption") or [],
    }

    await manager.async_update(starter)
    log.info(
        "owlwatt: configured HA Energy with solar source %s + forecast %s",
        lifetime_entity_id, entry.entry_id,
    )
    return True

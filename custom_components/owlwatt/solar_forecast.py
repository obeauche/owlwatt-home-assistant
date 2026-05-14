"""HA Energy ``solar_forecast`` platform contract for OwlWatt.

Home Assistant's Energy dashboard discovers solar forecast providers by
calling ``async_get_solar_forecast`` on each integration's module. We
re-export the function from ``__init__.py`` so it resolves under the
``owlwatt`` integration namespace, and keep the implementation here.

Expected return shape (HA contract):
    {"wh_hours": {"<ISO 8601 timestamp>": <wh number>, ...}}

OwlWatt's cloud snapshot ships ``solar_forecast_hourly`` as a list of
``{"ts": "<ISO>", "wh": <number>}`` entries — we re-key it.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant

from .const import DOMAIN

log = logging.getLogger(__name__)


async def async_get_solar_forecast(
    hass: HomeAssistant, config_entry_id: str
) -> Optional[dict[str, Any]]:
    """Return hourly solar forecast for HA Energy.

    Returns None when no data is available (HA Energy then hides the
    integration from the Solar Forecast dropdown for this entry).
    """
    domain_data = hass.data.get(DOMAIN, {})
    entry_data = domain_data.get(config_entry_id)
    if entry_data is None:
        return None
    coordinator = entry_data.get("coordinator")
    if coordinator is None or coordinator.data is None:
        return None
    hourly = coordinator.data.get("solar_forecast_hourly") or []
    if not hourly:
        return None
    return {
        "wh_hours": {
            entry["ts"]: float(entry["wh"])
            for entry in hourly
            if "ts" in entry and "wh" in entry
        }
    }

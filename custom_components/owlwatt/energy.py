"""Energy platform — HA Energy dashboard's `solar_forecast` contract.

HA Energy discovers solar-forecast providers by calling
``async_process_integration_platforms(hass, "energy", ...)`` which scans
every integration for a module named ``energy.py``. The callback inspects
THAT module (not __init__.py) for ``async_get_solar_forecast``. Reference
impl: homeassistant/components/forecast_solar/energy.py.

Putting the function on the integration's __init__.py module does NOT
register the integration as a forecast provider — discovery only fires
for the sub-platform module.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_solar_forecast(
    hass: HomeAssistant, config_entry_id: str
) -> dict | None:
    """Return hourly Wh forecast keyed by ISO timestamp.

    Cloud snapshot ships ``solar_forecast_hourly`` as a list of
    ``{"ts": ..., "wh": ...}``; HA Energy expects
    ``{"wh_hours": {ISO: wh, ...}}``.

    Returns None when no forecast is available so HA Energy hides this
    integration from the Solar Forecast dropdown for this entry.
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

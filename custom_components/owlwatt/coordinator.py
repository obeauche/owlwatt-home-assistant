"""OwlWatt DataUpdateCoordinator — polls /api/ha/v1/snapshot every 5 min."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import OwlWattApiClient, OwlWattAuthError, OwlWattRateLimited, OwlWattApiError
from .const import DEFAULT_POLL_INTERVAL_MINUTES, DOMAIN

log = logging.getLogger(__name__)

_HEARTBEAT_INTERVAL = timedelta(hours=24)


class OwlWattCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinates polling of the OwlWatt cloud snapshot endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: OwlWattApiClient,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            log,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_POLL_INTERVAL_MINUTES),
        )
        self.api_client = api_client
        self.entry = entry
        self._last_heartbeat: datetime | None = None
        self._first_poll_done = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch snapshot from cloud; raise HA-native exceptions on error."""
        try:
            snapshot = await self.api_client.get_snapshot()
        except OwlWattAuthError as exc:
            # Token revoked or invalid — HA core handles reauth flow
            raise ConfigEntryAuthFailed("OwlWatt token is no longer valid") from exc
        except OwlWattRateLimited as exc:
            raise UpdateFailed(
                f"OwlWatt rate limited; retry in {exc.retry_after_seconds}s"
            ) from exc
        except OwlWattApiError as exc:
            raise UpdateFailed(f"OwlWatt API error: {exc}") from exc

        # Fire heartbeat on first poll and every 24 h thereafter
        now = datetime.utcnow()
        if (
            not self._first_poll_done
            or self._last_heartbeat is None
            or (now - self._last_heartbeat) >= _HEARTBEAT_INTERVAL
        ):
            self._first_poll_done = True
            asyncio.ensure_future(self._async_send_heartbeat())
            self._last_heartbeat = now

        return snapshot

    async def _async_send_heartbeat(self) -> None:
        """Send heartbeat to cloud (best-effort; never raises)."""
        try:
            ha_version = self.hass.config.as_dict().get("version", "unknown")
            await self.api_client.post_heartbeat(str(ha_version))
            log.debug("owlwatt: heartbeat sent")
        except Exception as exc:
            # Heartbeat is non-critical; log and ignore
            log.debug("owlwatt: heartbeat failed (non-fatal): %s", exc)

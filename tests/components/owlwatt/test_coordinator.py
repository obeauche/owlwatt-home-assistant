"""Tests for OwlWattCoordinator.

Covers:
- First refresh succeeds -> data is stored
- 401 -> raises ConfigEntryAuthFailed
- 429 -> raises UpdateFailed with retry_after in message
- Heartbeat is fired on first poll
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.owlwatt.api_client import OwlWattAuthError, OwlWattRateLimited, OwlWattApiError
from custom_components.owlwatt.coordinator import OwlWattCoordinator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_coordinator(snapshot=None, side_effect=None):
    hass = MagicMock()
    hass.config.as_dict.return_value = {"version": "2024.1.0"}
    entry = MagicMock()
    entry.entry_id = "test-entry"

    api_client = MagicMock()
    if side_effect:
        api_client.get_snapshot = AsyncMock(side_effect=side_effect)
    else:
        api_client.get_snapshot = AsyncMock(return_value=snapshot or {})
    api_client.post_heartbeat = AsyncMock(return_value=None)

    coordinator = OwlWattCoordinator(hass, api_client, entry)
    return coordinator, api_client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_refresh_stores_data():
    """Successful first refresh stores snapshot data."""
    snapshot = {"tier": "trial", "production": {"current_w": 100.0}}
    coordinator, api_client = _make_coordinator(snapshot=snapshot)

    with patch.object(coordinator, "_async_refresh", wraps=coordinator._async_refresh):
        data = await coordinator._async_update_data()

    assert data["tier"] == "trial"
    assert data["production"]["current_w"] == 100.0


@pytest.mark.asyncio
async def test_auth_error_raises_config_entry_auth_failed():
    """401 from cloud raises ConfigEntryAuthFailed."""
    coordinator, _ = _make_coordinator(side_effect=OwlWattAuthError("revoked"))

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_rate_limited_raises_update_failed():
    """429 raises UpdateFailed with retry_after in message."""
    coordinator, _ = _make_coordinator(
        side_effect=OwlWattRateLimited(retry_after_seconds=120.0)
    )

    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_data()

    assert "120" in str(exc_info.value)


@pytest.mark.asyncio
async def test_api_error_raises_update_failed():
    """Generic API error raises UpdateFailed."""
    coordinator, _ = _make_coordinator(
        side_effect=OwlWattApiError("server 500")
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_heartbeat_fired_on_first_poll():
    """Heartbeat is sent on the first successful poll."""
    snapshot = {"tier": "trial"}
    coordinator, api_client = _make_coordinator(snapshot=snapshot)

    assert not coordinator._first_poll_done
    assert coordinator._last_heartbeat is None

    with patch("asyncio.ensure_future") as mock_future:
        await coordinator._async_update_data()

    assert coordinator._first_poll_done
    assert coordinator._last_heartbeat is not None
    mock_future.assert_called_once()


@pytest.mark.asyncio
async def test_heartbeat_not_fired_on_second_poll_within_24h():
    """Heartbeat is NOT re-fired within 24 h of first poll."""
    snapshot = {"tier": "trial"}
    coordinator, api_client = _make_coordinator(snapshot=snapshot)

    with patch("asyncio.ensure_future"):
        await coordinator._async_update_data()  # first poll -> heartbeat

    with patch("asyncio.ensure_future") as mock_future:
        await coordinator._async_update_data()  # second poll -> no heartbeat

    mock_future.assert_not_called()

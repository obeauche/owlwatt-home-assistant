"""Tests for the OwlWatt referral button entity (Phase 6).

Covers:
- Button entity is registered under the correct unique_id and name
- On press: triggers persistent_notification.create
- On press: referral URL includes customer_id when manifest returns it
- On press: referral URL falls back to no referrer when manifest call fails
- On press: service failures are swallowed (never raises)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.owlwatt.button import OwlWattReferFriendButton, _REFER_BASE_URL
from custom_components.owlwatt.const import DOMAIN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_coordinator(snapshot: dict | None = None):
    coordinator = MagicMock()
    coordinator.data = snapshot or {}
    coordinator.last_update_success = True
    coordinator.api_client = MagicMock()
    return coordinator


def _mock_entry(entry_id: str = "test-entry"):
    entry = MagicMock()
    entry.entry_id = entry_id
    return entry


def _mock_hass():
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=False)
    return hass


# ---------------------------------------------------------------------------
# Entity registration
# ---------------------------------------------------------------------------

def test_button_entity_unique_id():
    """Button has entry-scoped unique_id."""
    coordinator = _mock_coordinator()
    entry = _mock_entry("my-entry-id")
    button = OwlWattReferFriendButton(coordinator, entry)
    assert button._attr_unique_id == "my-entry-id_refer_friend"


def test_button_entity_name():
    """Button friendly name matches spec."""
    coordinator = _mock_coordinator()
    entry = _mock_entry()
    button = OwlWattReferFriendButton(coordinator, entry)
    assert button._attr_name == "Refer a friend to OwlWatt"


def test_button_device_info():
    """Button shares device_info with the rest of the OwlWatt entity cluster."""
    coordinator = _mock_coordinator()
    entry = _mock_entry("eid")
    button = OwlWattReferFriendButton(coordinator, entry)
    di = button._attr_device_info
    assert (DOMAIN, "eid") in di["identifiers"]


# ---------------------------------------------------------------------------
# async_setup_entry registers the button
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_setup_entry_adds_button():
    """async_setup_entry calls async_add_entities with one OwlWattReferFriendButton."""
    from custom_components.owlwatt.button import async_setup_entry

    hass = _mock_hass()
    entry = _mock_entry("setup-eid")
    coordinator = _mock_coordinator()
    hass.data = {DOMAIN: {"setup-eid": {"coordinator": coordinator}}}

    added = []

    def _fake_add(entities, update_before_add=False):
        added.extend(entities)

    await async_setup_entry(hass, entry, _fake_add)

    assert len(added) == 1
    assert isinstance(added[0], OwlWattReferFriendButton)


# ---------------------------------------------------------------------------
# async_press behaviour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_press_fires_persistent_notification():
    """Pressing the button emits a persistent_notification.create call."""
    coordinator = _mock_coordinator()
    coordinator.api_client.get_manifest = AsyncMock(return_value={"customer_id": 42})
    entry = _mock_entry()
    button = OwlWattReferFriendButton(coordinator, entry)
    button.hass = _mock_hass()

    await button.async_press()

    button.hass.services.async_call.assert_called()
    call_args = button.hass.services.async_call.call_args_list
    # First call should be persistent_notification.create
    first_call = call_args[0]
    assert first_call[0][0] == "persistent_notification"
    assert first_call[0][1] == "create"
    payload = first_call[0][2]
    assert "owlwatt.com/refer" in payload["message"]
    assert "from=ha" in payload["message"]


@pytest.mark.asyncio
async def test_press_url_includes_customer_id_from_manifest():
    """When manifest returns customer_id, referral URL contains referrer= param."""
    coordinator = _mock_coordinator()
    coordinator.api_client.get_manifest = AsyncMock(return_value={"customer_id": 99})
    entry = _mock_entry()
    button = OwlWattReferFriendButton(coordinator, entry)
    button.hass = _mock_hass()

    await button.async_press()

    call_args = button.hass.services.async_call.call_args_list
    first_call = call_args[0]
    payload = first_call[0][2]
    assert "referrer=99" in payload["message"]


@pytest.mark.asyncio
async def test_press_url_fallback_without_customer_id():
    """When manifest call fails, URL omits referrer= but press still completes."""
    coordinator = _mock_coordinator()
    coordinator.api_client.get_manifest = AsyncMock(side_effect=Exception("network error"))
    entry = _mock_entry()
    button = OwlWattReferFriendButton(coordinator, entry)
    button.hass = _mock_hass()

    await button.async_press()  # must not raise

    call_args = button.hass.services.async_call.call_args_list
    first_call = call_args[0]
    payload = first_call[0][2]
    assert "from=ha" in payload["message"]
    assert "referrer=" not in payload["message"]


@pytest.mark.asyncio
async def test_press_notification_failure_does_not_raise():
    """If persistent_notification service throws, async_press still completes."""
    coordinator = _mock_coordinator()
    coordinator.api_client.get_manifest = AsyncMock(return_value={"customer_id": 1})
    entry = _mock_entry()
    button = OwlWattReferFriendButton(coordinator, entry)
    button.hass = _mock_hass()
    button.hass.services.async_call = AsyncMock(side_effect=Exception("svc error"))

    # Should not raise
    await button.async_press()


@pytest.mark.asyncio
async def test_press_opens_frontend_url_if_service_available():
    """If frontend.open_url service exists, it is called with the referral URL."""
    coordinator = _mock_coordinator()
    coordinator.api_client.get_manifest = AsyncMock(return_value={"customer_id": 7})
    entry = _mock_entry()
    button = OwlWattReferFriendButton(coordinator, entry)
    button.hass = _mock_hass()

    def _has_service(domain, service):
        return domain == "frontend" and service == "open_url"

    button.hass.services.has_service = MagicMock(side_effect=_has_service)

    await button.async_press()

    calls = button.hass.services.async_call.call_args_list
    domains = [c[0][0] for c in calls]
    assert "frontend" in domains

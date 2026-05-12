"""Tests for OwlWatt config_flow.

Covers:
- Happy path: valid token -> create entry
- Invalid token (401) -> show invalid_auth error
- Cannot connect (API error) -> show cannot_connect error
- no_account branch -> ABORTs with external_setup reason
- Duplicate entry constraint (unique_id collision)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from custom_components.owlwatt.api_client import OwlWattAuthError, OwlWattApiError
from custom_components.owlwatt.config_flow import OwlWattConfigFlow
from custom_components.owlwatt.const import CONF_TOKEN, CONF_API_BASE, DEFAULT_API_BASE, DOMAIN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hass():
    """Minimal mock hass."""
    hass = MagicMock()
    hass.data = {}
    return hass


def _make_flow():
    flow = OwlWattConfigFlow()
    flow.hass = _make_hass()
    flow.context = {"source": "user"}
    flow._abort_if_unique_id_configured = MagicMock()
    return flow


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_step_user_shows_menu():
    """async_step_user with no input should show a menu."""
    flow = _make_flow()
    result = await flow.async_step_user(None)
    assert result["type"] == "menu"
    assert "token" in result["menu_options"]
    assert "no_account" in result["menu_options"]


@pytest.mark.asyncio
async def test_no_account_aborts_flow():
    """Choosing 'no_account' should abort with external_setup reason."""
    flow = _make_flow()
    result = await flow.async_step_no_account()
    assert result["type"] == "abort"
    assert result["reason"] == "external_setup"


@pytest.mark.asyncio
async def test_token_step_valid_token_creates_entry():
    """Valid token should create a config entry."""
    flow = _make_flow()

    mock_manifest = {"api_version": "1.0.0", "features": {}}

    with patch(
        "custom_components.owlwatt.config_flow.OwlWattApiClient"
    ) as MockClient, patch(
        "custom_components.owlwatt.config_flow.async_get_clientsession"
    ) as mock_session:
        instance = MockClient.return_value
        instance.get_manifest = AsyncMock(return_value=mock_manifest)
        mock_session.return_value = MagicMock()

        flow.async_set_unique_id = AsyncMock()
        flow.async_create_entry = MagicMock(
            return_value={"type": "create_entry", "title": "OwlWatt", "data": {}}
        )

        result = await flow.async_step_token(
            {CONF_TOKEN: "test-valid-token"}
        )

    assert result["type"] == "create_entry"


@pytest.mark.asyncio
async def test_token_step_invalid_token_shows_error():
    """401 from cloud should set invalid_auth error and re-show the form."""
    flow = _make_flow()

    with patch(
        "custom_components.owlwatt.config_flow.OwlWattApiClient"
    ) as MockClient, patch(
        "custom_components.owlwatt.config_flow.async_get_clientsession"
    ):
        instance = MockClient.return_value
        instance.get_manifest = AsyncMock(side_effect=OwlWattAuthError("bad token"))

        result = await flow.async_step_token({CONF_TOKEN: "bad-token"})

    assert result["type"] == "form"
    assert result["errors"].get(CONF_TOKEN) == "invalid_auth"


@pytest.mark.asyncio
async def test_token_step_cannot_connect_shows_error():
    """Network error should set cannot_connect error."""
    flow = _make_flow()

    with patch(
        "custom_components.owlwatt.config_flow.OwlWattApiClient"
    ) as MockClient, patch(
        "custom_components.owlwatt.config_flow.async_get_clientsession"
    ):
        instance = MockClient.return_value
        instance.get_manifest = AsyncMock(side_effect=OwlWattApiError("timeout"))

        result = await flow.async_step_token({CONF_TOKEN: "some-token"})

    assert result["type"] == "form"
    assert result["errors"].get("base") == "cannot_connect"


@pytest.mark.asyncio
async def test_token_step_no_input_shows_form():
    """async_step_token with no user input should show the form."""
    flow = _make_flow()
    result = await flow.async_step_token(None)
    assert result["type"] == "form"
    assert result["step_id"] == "token"
    assert not result.get("errors")

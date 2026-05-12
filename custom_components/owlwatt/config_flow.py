"""Config flow for OwlWatt integration.

Two-step flow:
  1. async_step_user: menu — "I have an account" -> async_step_token
                             "I don't have one yet" -> async_step_no_account
  2. async_step_token: validate token via GET /api/ha/v1/manifest;
                       on success -> create_entry.

Unique entry ID: sha256(api_base + ":" + token)[:16] — prevents duplicate
entries for the same account.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional
import webbrowser

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import OwlWattApiClient, OwlWattAuthError, OwlWattApiError, OwlWattRateLimited
from .const import CONF_API_BASE, CONF_TOKEN, DEFAULT_API_BASE, DOMAIN

log = logging.getLogger(__name__)

_NO_ACCOUNT_URL = "https://owlwatt.com/ha?ref=hacs"


def _unique_id(api_base: str, token: str) -> str:
    """Stable unique ID from (api_base, token) pair — prevents duplicate entries."""
    raw = f"{api_base.rstrip('/')}:{token}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class OwlWattConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for OwlWatt."""

    VERSION = 1

    def __init__(self) -> None:
        self._api_base = DEFAULT_API_BASE

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Step 1: present menu to user."""
        if user_input is not None:
            choice = user_input.get("next_step_id")
            if choice == "token":
                return await self.async_step_token()
            if choice == "no_account":
                return await self.async_step_no_account()

        return self.async_show_menu(
            step_id="user",
            menu_options=["token", "no_account"],
        )

    async def async_step_no_account(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Open owlwatt.com/ha in the browser and abort the flow."""
        return self.async_abort(
            reason="external_setup",
            description_placeholders={"url": _NO_ACCOUNT_URL},
        )

    async def async_step_token(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> FlowResult:
        """Step 2: accept and validate an API token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            token: str = (user_input.get(CONF_TOKEN) or "").strip()
            api_base: str = (
                user_input.get(CONF_API_BASE) or DEFAULT_API_BASE
            ).rstrip("/")

            # Validate token by calling the manifest endpoint
            session = async_get_clientsession(self.hass)
            client = OwlWattApiClient(session, token, api_base)
            try:
                await client.get_manifest()
            except OwlWattAuthError:
                errors[CONF_TOKEN] = "invalid_auth"
            except OwlWattRateLimited:
                errors["base"] = "rate_limited"
            except OwlWattApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                log.exception("Unexpected error in OwlWatt config flow")
                errors["base"] = "unknown"

            if not errors:
                uid = _unique_id(api_base, token)
                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="OwlWatt",
                    data={
                        CONF_TOKEN: token,
                        CONF_API_BASE: api_base,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN): str,
            }
        )

        return self.async_show_form(
            step_id="token",
            data_schema=schema,
            errors=errors,
        )

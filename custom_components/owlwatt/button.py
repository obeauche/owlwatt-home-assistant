"""OwlWatt button entities.

Phase 6 placeholder — referral button stub.
The button opens owlwatt.com/refer?from=ha&referrer=<customer_id>.
Implementation deferred to Phase 6 (Synergy #7).
"""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OwlWattCoordinator

log = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Phase 6 placeholder — no button entities in v0.1.0."""
    # Referral button implementation deferred to Phase 6.
    # Uncomment when Phase 6 is implemented:
    # coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    # async_add_entities([OwlWattReferFriendButton(coordinator, entry)])
    pass

"""Minimal Home Assistant stubs for running unit tests without a full HA install.

These are imported by conftest.py at the test session level via sys.modules mocking.
Only the minimal surface needed by the OwlWatt integration tests is stubbed.
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock


STATE_UNAVAILABLE = "unavailable"
STATE_UNKNOWN = "unknown"


def _make_module(name: str, **attrs) -> ModuleType:
    m = ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m


def install_stubs() -> None:
    """Install minimal HA stubs into sys.modules."""
    if "homeassistant" in sys.modules:
        return  # already installed (real HA or previous stub run)

    # --- homeassistant ---
    ha = ModuleType("homeassistant")
    ha.__path__ = []
    sys.modules["homeassistant"] = ha

    # homeassistant.const
    ha_const = _make_module(
        "homeassistant.const",
        STATE_UNAVAILABLE=STATE_UNAVAILABLE,
        STATE_UNKNOWN=STATE_UNKNOWN,
        CONF_URL="url",
    )
    sys.modules["homeassistant.const"] = ha_const

    # homeassistant.exceptions
    class ConfigEntryAuthFailed(Exception):
        pass

    ha_exc = _make_module(
        "homeassistant.exceptions",
        ConfigEntryAuthFailed=ConfigEntryAuthFailed,
    )
    sys.modules["homeassistant.exceptions"] = ha_exc

    # homeassistant.core
    class HomeAssistant:
        def __init__(self):
            self.config = MagicMock()
            self.data = {}
            self.services = MagicMock()
    class ServiceCall:
        pass

    ha_core = _make_module(
        "homeassistant.core",
        HomeAssistant=HomeAssistant,
        ServiceCall=ServiceCall,
    )
    sys.modules["homeassistant.core"] = ha_core

    # homeassistant.config_entries
    class ConfigEntry:
        entry_id: str = "test"
        data: dict = {}
    class ConfigFlow:
        hass: "HomeAssistant" = None
        context: dict = {}

        def __init_subclass__(cls, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)

        def async_show_form(self, **kw):
            return {"type": "form", **kw}
        def async_create_entry(self, **kw):
            return {"type": "create_entry", **kw}
        def async_abort(self, **kw):
            return {"type": "abort", **kw}
        def async_show_menu(self, **kw):
            return {"type": "menu", **kw}
        def _abort_if_unique_id_configured(self):
            pass
        async def async_set_unique_id(self, uid):
            pass

    ha_ce = _make_module(
        "homeassistant.config_entries",
        ConfigEntry=ConfigEntry,
        ConfigFlow=ConfigFlow,
        config_entries=MagicMock(),
    )
    sys.modules["homeassistant.config_entries"] = ha_ce

    # homeassistant.data_entry_flow
    ha_flow = _make_module("homeassistant.data_entry_flow", FlowResult=dict)
    sys.modules["homeassistant.data_entry_flow"] = ha_flow

    # homeassistant.helpers
    ha_helpers = ModuleType("homeassistant.helpers")
    ha_helpers.__path__ = []
    sys.modules["homeassistant.helpers"] = ha_helpers

    class DeviceInfo(dict):
        def __init__(self, **kw):
            super().__init__(**kw)

    ha_entity = _make_module("homeassistant.helpers.entity", DeviceInfo=DeviceInfo)
    sys.modules["homeassistant.helpers.entity"] = ha_entity

    ha_ep = _make_module(
        "homeassistant.helpers.entity_platform",
        AddEntitiesCallback=MagicMock,
    )
    sys.modules["homeassistant.helpers.entity_platform"] = ha_ep

    ha_ac = _make_module(
        "homeassistant.helpers.aiohttp_client",
        async_get_clientsession=MagicMock(return_value=MagicMock()),
    )
    sys.modules["homeassistant.helpers.aiohttp_client"] = ha_ac

    # homeassistant.helpers.update_coordinator
    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, logger, *, name, update_interval):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data = None
            self.last_update_success = True

        async def _async_update_data(self):
            raise NotImplementedError

        async def async_request_refresh(self):
            self.data = await self._async_update_data()

        async def _async_refresh(self, *a, **kw):
            pass

        async def async_config_entry_first_refresh(self):
            self.data = await self._async_update_data()

    class CoordinatorEntity:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, coordinator):
            self.coordinator = coordinator

        @property
        def available(self):
            return self.coordinator.last_update_success

    ha_uc = _make_module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=DataUpdateCoordinator,
        CoordinatorEntity=CoordinatorEntity,
        UpdateFailed=UpdateFailed,
    )
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_uc

    # homeassistant.components.sensor
    from enum import Enum

    class SensorDeviceClass(str, Enum):
        POWER = "power"
        ENERGY = "energy"
        MONETARY = "monetary"
        DURATION = "duration"
        ENUM = "enum"
        TIMESTAMP = "timestamp"

    class SensorStateClass(str, Enum):
        MEASUREMENT = "measurement"
        TOTAL = "total"
        TOTAL_INCREASING = "total_increasing"

    class SensorEntity:
        device_class = None
        state_class = None
        native_unit_of_measurement = None
        _attr_has_entity_name = False
        _attr_name = None
        _attr_unique_id = None
        _attr_device_info = None
        _attr_device_class = None
        _attr_state_class = None
        _attr_native_unit_of_measurement = None
        _attr_options = None

        def __init__(self):
            pass

        @property
        def device_class(self):
            return self._attr_device_class

        @property
        def extra_state_attributes(self):
            return {}

        @property
        def native_value(self):
            return None

    ha_sensor = _make_module(
        "homeassistant.components.sensor",
        SensorDeviceClass=SensorDeviceClass,
        SensorEntity=SensorEntity,
        SensorStateClass=SensorStateClass,
    )
    sys.modules["homeassistant.components.sensor"] = ha_sensor

    ha_components = ModuleType("homeassistant.components")
    ha_components.__path__ = []
    sys.modules["homeassistant.components"] = ha_components

    # homeassistant.components.binary_sensor
    class BinarySensorDeviceClass(str, Enum):
        PROBLEM = "problem"
        MOTION = "motion"

    class BinarySensorEntity:
        _attr_has_entity_name = False
        _attr_name = None
        _attr_unique_id = None
        _attr_device_info = None
        _attr_device_class = None

        def __init__(self):
            pass

        @property
        def device_class(self):
            return self._attr_device_class

        @property
        def is_on(self):
            return None

        @property
        def extra_state_attributes(self):
            return {}

    ha_bs = _make_module(
        "homeassistant.components.binary_sensor",
        BinarySensorDeviceClass=BinarySensorDeviceClass,
        BinarySensorEntity=BinarySensorEntity,
    )
    sys.modules["homeassistant.components.binary_sensor"] = ha_bs

    # homeassistant.components.camera
    class Camera:
        def __init__(self):
            pass
        @property
        def available(self):
            return True
        @property
        def extra_state_attributes(self):
            return {}
        async def async_camera_image(self, width=None, height=None):
            return None

    ha_cam = _make_module(
        "homeassistant.components.camera",
        Camera=Camera,
    )
    sys.modules["homeassistant.components.camera"] = ha_cam

    # homeassistant.components.image
    class ImageEntity:
        def __init__(self, hass):
            self.hass = hass
        @property
        def available(self):
            return True
        @property
        def extra_state_attributes(self):
            return {}
        async def async_image(self):
            return None

    ha_img = _make_module(
        "homeassistant.components.image",
        ImageEntity=ImageEntity,
    )
    sys.modules["homeassistant.components.image"] = ha_img

    # homeassistant.components.button
    class ButtonEntity:
        def __init__(self):
            pass

    ha_btn = _make_module(
        "homeassistant.components.button",
        ButtonEntity=ButtonEntity,
    )
    sys.modules["homeassistant.components.button"] = ha_btn

    # UnitOf* constants
    class UnitOfPower:
        WATT = "W"
        KILO_WATT = "kW"

    class UnitOfEnergy:
        KILO_WATT_HOUR = "kWh"
        WATT_HOUR = "Wh"

    class UnitOfTime:
        SECONDS = "s"
        MINUTES = "min"
        HOURS = "h"
        DAYS = "d"

    ha_const.UnitOfPower = UnitOfPower
    ha_const.UnitOfEnergy = UnitOfEnergy
    ha_const.UnitOfTime = UnitOfTime

    # voluptuous stub
    if "voluptuous" not in sys.modules:
        vol = ModuleType("voluptuous")
        class Schema:
            def __init__(self, schema):
                self._schema = schema
            def __call__(self, data):
                return data
        class Required:
            def __init__(self, key):
                self.key = key
            def __hash__(self):
                return hash(self.key)
            def __eq__(self, other):
                return self.key == other
        vol.Schema = Schema
        vol.Required = Required
        sys.modules["voluptuous"] = vol

    # homeassistant.components.persistent_notification
    def async_create(hass, message="", title="", notification_id=None):
        pass  # no-op stub; tests that care mock this explicitly

    ha_pn = _make_module(
        "homeassistant.components.persistent_notification",
        async_create=async_create,
    )
    sys.modules["homeassistant.components.persistent_notification"] = ha_pn

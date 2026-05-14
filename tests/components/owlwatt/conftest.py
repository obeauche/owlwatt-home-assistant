"""Shared fixtures for OwlWatt HA integration tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# ---------------------------------------------------------------------------
# Snapshot fixtures
# ---------------------------------------------------------------------------

TRIAL_SNAPSHOT = {
    "tier": "trial",
    "tier_label": "30-day Trial — Day 14 of 30",
    "as_of": "2026-05-12T13:14:00+00:00",
    "production": {
        "current_w": 4123.0,
        "today_kwh": 18.4,
        "month_kwh": 412.7,
        "stale": False,
    },
    "expected": {
        "today_kwh": 22.1,
        "month_kwh": 460.0,
        "method_label": "Independent measurement",
    },
    "shortfall": {
        "today_pct": 16.7,
        "month_pct": 10.3,
        "month_kwh": 47.3,
    },
    "claim": {
        "available": True,
        "value_locked": True,
        "unlock_url": "https://owlwatt.com/app/dashboard?upsell=ha",
    },
    "anomaly": {"active": False, "label": None},
    "system": {
        "kw_dc": 9.6,
        "install_date": "2024-03-29",
        "tilt_deg": 25,
        "azimuth_deg": 180,
    },
    "solar_lifetime_kwh": 12345.6,
    "solar_forecast_hourly": [
        {"ts": "2026-05-12T13:00:00+00:00", "wh": 4500.0},
        {"ts": "2026-05-12T14:00:00+00:00", "wh": 4800.0},
        {"ts": "2026-05-12T15:00:00+00:00", "wh": 4200.0},
    ],
}

PAID_SNAPSHOT = {
    "tier": "monthly",
    "tier_label": "Monthly Plan",
    "as_of": "2026-05-12T13:14:00+00:00",
    "production": {
        "current_w": 4123.0,
        "today_kwh": 18.4,
        "month_kwh": 412.7,
        "stale": False,
    },
    "expected": {
        "today_kwh": 22.1,
        "month_kwh": 460.0,
        "method_label": "Independent measurement",
    },
    "shortfall": {
        "today_pct": 16.7,
        "month_pct": 10.3,
        "month_kwh": 47.3,
    },
    "claim": {
        "available": True,
        "value_locked": False,
        "value_low_usd": 308.5,
        "value_high_usd": 411.4,
        "value_display_text": "$308 – $411",
        "method_label": "Independent measurement",
        "report_url": "https://owlwatt.com/app/dashboard?tab=claims",
    },
    "anomaly": {"active": False, "label": None},
    "system": {
        "kw_dc": 9.6,
        "install_date": "2024-03-29",
        "tilt_deg": 25,
        "azimuth_deg": 180,
    },
    "roof_image": {
        "url_template": "/api/ha/v1/roof/image?ts=<epoch>",
        "last_baked_at": "2026-04-22T10:00:00+00:00",
    },
    "solar_lifetime_kwh": 12345.6,
    "solar_forecast_hourly": [
        {"ts": "2026-05-12T13:00:00+00:00", "wh": 4500.0},
        {"ts": "2026-05-12T14:00:00+00:00", "wh": 4800.0},
        {"ts": "2026-05-12T15:00:00+00:00", "wh": 4200.0},
    ],
}


@pytest.fixture
def trial_snapshot():
    return dict(TRIAL_SNAPSHOT)


@pytest.fixture
def paid_snapshot():
    return dict(PAID_SNAPSHOT)


# ---------------------------------------------------------------------------
# Install HA stubs before any test imports homeassistant.*
# This allows tests to run without a full Home Assistant installation.
# ---------------------------------------------------------------------------

from tests.components.owlwatt.ha_stubs import install_stubs
install_stubs()

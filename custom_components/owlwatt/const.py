"""Constants for the OwlWatt integration."""

DOMAIN = "owlwatt"

# Default cloud API base URL.  Points directly to the Fly.io app while
# owlwatt.com TLS cert coverage is confirmed.  Change to "https://owlwatt.com"
# once the cert covers the API subdomain (parent session decision).
DEFAULT_API_BASE = "https://owlwatt-api.fly.dev"

# How often to poll the cloud snapshot endpoint.
DEFAULT_POLL_INTERVAL_MINUTES = 5

# ConfigEntry data keys.
CONF_TOKEN = "token"
CONF_API_BASE = "api_base"

# Disclaimer shown as an attribute on every paid-tier claim-value sensor.
# Text is factual only — no legal claims, no installer blame.
# Mirrors cloud app/routers/ha_integration.py:MEASUREMENT_DISCLAIMER_SHORT.
MEASUREMENT_DISCLAIMER_SHORT = (
    "This measurement is informational. Actual recovery depends on your "
    "installer agreement and applicable law. Consult a licensed attorney "
    "for legal advice."
)

# Friendly names per 06-marketing-copy-canonical.md §4.
SENSOR_FRIENDLY_NAMES: dict[str, str] = {
    "production_now": "Solar production right now",
    "production_today": "Solar production today",
    "production_month": "Solar production this month",
    "expected_today": "Expected solar today",
    "expected_month": "Expected solar this month",
    "shortfall_today_pct": "Solar shortfall today (percent)",
    "shortfall_month_pct": "Solar shortfall this month (percent)",
    "shortfall_month_kwh": "Solar shortfall this month (kWh)",
    "data_freshness": "OwlWatt data freshness",
    "subscription_tier": "OwlWatt subscription",
    "trial_days_remaining": "OwlWatt trial days remaining",
    "claim_value_low_usd": "Documented shortfall value (low)",
    "claim_value_high_usd": "Documented shortfall value (high)",
    "claim_value_display_text": "Documented shortfall value",
    "claim_status": "Claim status",
    "active_claims_count": "Open claims",
    "anomaly_label": "Anomaly detail",
}

BINARY_SENSOR_FRIENDLY_NAMES: dict[str, str] = {
    "data_stale": "OwlWatt data is stale",
    "anomaly_active": "Solar anomaly",
}

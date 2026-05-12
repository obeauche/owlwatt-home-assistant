# OwlWatt for Home Assistant

Independent solar production measurement, surfaced as Home Assistant sensors.

OwlWatt independently measures whether your solar system produces what
it was promised to produce. This integration brings that measurement
into Home Assistant — production now, expected production, shortfall,
anomaly detection, and (for paid subscribers) claim documentation
against your installer's production guarantee.

Free integration. Open source. Subscription is optional and managed at
owlwatt.com — not in this integration.

## What you get

- Current solar production (W) and daily/monthly totals (kWh)
- Expected production based on independent measurement
- Shortfall detection: percent and kilowatt-hours
- Anomaly flags (soiling, string offline, weather-adjusted underperformance)
- Trial subscribers see all measurement data
- Paid subscribers additionally see:
  - Claim value in dollars
  - Pre-filled installer claim emails
  - Live status of any open claim
  - Roof imagery (baked from satellite + aerial sources)
- All standard HA device classes — energy, power, monetary — so
  everything works with the HA Energy dashboard, Alexa, Google Home,
  and HomeKit Bridge out of the box

## What this integration is not

- Not a replacement for your Enphase/SolarEdge app — your inverter
  vendor is the source of raw telemetry
- Not a calculation that runs in Home Assistant. Expected production
  is computed in the OwlWatt cloud using independent methodology;
  this integration only displays the result
- Not a payment system. OwlWatt does not pay shortfalls. It documents
  them so you can pursue the production guarantee your installer or
  dealer originally offered you

## Installation

1. Add this repository in HACS as a custom integration
2. Restart Home Assistant
3. Settings -> Devices & Services -> Add Integration -> OwlWatt
4. If you already have an OwlWatt account:
   - At owlwatt.com, go to Account Settings -> Home Assistant
   - Click "Create API token", copy the token (shown once)
   - Paste it into the Home Assistant config dialog
5. If you don't have an OwlWatt account yet:
   - Click "I don't have an account yet" in the config dialog
   - Your browser opens owlwatt.com/ha to start a 30-day free trial
   - Come back and complete setup once your account is active

---

OwlWatt is an independent measurement service. We are not affiliated
with any solar installer, panel manufacturer, or inverter vendor.

The OwlWatt cloud is operated by Olivier Beauchemin, sole proprietor.
See owlwatt.com/privacy and owlwatt.com/terms for the full agreement
governing your account.

This integration is licensed under MIT. The OwlWatt service is a paid
subscription managed separately at owlwatt.com.

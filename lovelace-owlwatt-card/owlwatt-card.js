/**
 * OwlWatt Lovelace Card (v0.2.0 — Phase 8)
 *
 * Displays real-time solar production vs expected + shortfall status.
 * For paid subscribers shows a "Share my OwlWatt solar" button that
 * calls the owlwatt.create_share_link HA service.
 *
 * The shared PNG shows only shortfall %, qualitative status, anonymized
 * geo-label and referral footer. No claim_value_usd scalar (C2 compliance).
 *
 * Uses safe DOM API only — no innerHTML with sensor/user data.
 *
 * Registration:
 *   resources:
 *     - url: /hacsfiles/lovelace-owlwatt-card/owlwatt-card.js
 *       type: module
 */

const OWLWATT_CARD_VERSION = "0.2.0";

const _STYLES = `
  :host { display: block; }
  .ow-card {
    padding: 16px;
    font-family: var(--primary-font-family, sans-serif);
    color: var(--primary-text-color);
  }
  .ow-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .ow-title { font-size: 1.1em; font-weight: 600; }
  .ow-badge {
    font-size: 0.75em; padding: 2px 8px; border-radius: 12px;
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  }
  .ow-badge-healthy  { background: #22c55e22; color: #22c55e; }
  .ow-badge-under    { background: #eab30822; color: #ca8a04; }
  .ow-badge-anomaly  { background: #ef444422; color: #ef4444; }
  .ow-badge-unknown  { background: #64748b22; color: #64748b; }
  .ow-stats {
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px;
  }
  .ow-stat-block { display: flex; flex-direction: column; }
  .ow-stat-label {
    font-size: 0.72em; color: var(--secondary-text-color);
    text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 2px;
  }
  .ow-stat-value { font-size: 1.4em; font-weight: 700; }
  .ow-bar-track {
    height: 8px; border-radius: 4px;
    background: var(--divider-color, #e2e8f0); overflow: hidden; margin-bottom: 6px;
  }
  .ow-bar-fill {
    height: 100%; border-radius: 4px;
    background: var(--state-icon-color, #0ea5e9); transition: width 0.5s ease;
  }
  .ow-shortfall {
    font-size: 0.78em; color: var(--secondary-text-color); margin-bottom: 12px;
  }
  .ow-share-row {
    display: flex; align-items: center; gap: 10px;
    border-top: 1px solid var(--divider-color, #e2e8f0); padding-top: 12px;
  }
  .ow-share-btn {
    flex: 1; padding: 7px 14px;
    border: 1px solid var(--primary-color, #0ea5e9); border-radius: 6px;
    background: transparent; color: var(--primary-color, #0ea5e9);
    font-size: 0.85em; font-weight: 600; cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }
  .ow-share-btn:hover { background: var(--primary-color, #0ea5e9); color: #fff; }
  .ow-share-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .ow-share-tip { font-size: 0.7em; color: var(--secondary-text-color); flex: 2; }
  .ow-upsell {
    font-size: 0.78em; color: var(--secondary-text-color);
    border-top: 1px solid var(--divider-color, #e2e8f0); padding-top: 10px;
  }
  .ow-upsell-link { color: var(--primary-color, #0ea5e9); text-decoration: none; font-weight: 600; }
  .ow-error { font-size: 0.8em; color: var(--error-color, #ef4444); margin-top: 8px; }
`;

function _el(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text != null) el.textContent = String(text);
  return el;
}

function _fmt_kwh(val) {
  if (val == null || isNaN(val)) return "—";
  return parseFloat(val).toFixed(1) + " kWh";
}

function _fmt_pct(val) {
  if (val == null || isNaN(val)) return "—";
  return parseFloat(val).toFixed(1) + "%";
}

function _bar_pct(today_kwh, expected_kwh) {
  if (today_kwh == null || expected_kwh == null || expected_kwh <= 0) return 0;
  return Math.min(100, (parseFloat(today_kwh) / parseFloat(expected_kwh)) * 100);
}

function _status(snapshot) {
  if (!snapshot) return "unknown";
  if (snapshot.anomaly && snapshot.anomaly.active) return "anomaly";
  const sf = snapshot.shortfall && snapshot.shortfall.today_pct;
  if (sf != null && parseFloat(sf) >= 10) return "under";
  return "healthy";
}

function _is_paid(snapshot) {
  if (!snapshot) return false;
  return snapshot.tier === "monthly" || snapshot.tier === "annual";
}

class OwlWattCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._shareInProgress = false;
    this._shareError = null;
  }

  static getConfigElement() {
    return document.createElement("owlwatt-card-editor");
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _getSnapshot() {
    if (!this._hass) return null;
    const tierEntity = this._hass.states["sensor.owlwatt_subscription_tier"];
    if (!tierEntity) return null;
    const attrs = tierEntity.attributes || {};
    return {
      tier: tierEntity.state,
      tier_label: attrs.tier_label || tierEntity.state,
      production: {
        today_kwh: this._num("sensor.owlwatt_production_today"),
        current_w: this._num("sensor.owlwatt_production_now"),
      },
      expected: {
        today_kwh: this._num("sensor.owlwatt_expected_today"),
      },
      shortfall: {
        today_pct: this._num("sensor.owlwatt_shortfall_today_pct"),
      },
      anomaly: {
        active: this._hass.states["binary_sensor.owlwatt_anomaly_active"]?.state === "on",
      },
      claim: {
        value_locked: attrs.paid_tier_required === true,
        unlock_url: attrs.unlock_url || "https://owlwatt.com/app/dashboard?upsell=ha",
      },
    };
  }

  _num(entity_id) {
    const s = this._hass && this._hass.states[entity_id];
    if (!s || s.state === "unavailable" || s.state === "unknown") return null;
    const n = parseFloat(s.state);
    return isNaN(n) ? null : n;
  }

  async _handleShare() {
    if (this._shareInProgress) return;
    this._shareInProgress = true;
    this._shareError = null;
    this._render();
    try {
      // The service handler fires a persistent_notification with the share URL.
      await this._hass.callService("owlwatt", "create_share_link", {});
    } catch (err) {
      this._shareError = "Could not create share link. Please try again.";
      console.error("[owlwatt-card] create_share_link error:", err);
    } finally {
      this._shareInProgress = false;
      this._render();
    }
  }

  _render() {
    const root = this.shadowRoot;
    if (!root) return;

    // Safe DOM clear — does not trigger XSS concerns
    while (root.firstChild) root.removeChild(root.firstChild);

    const style = document.createElement("style");
    style.textContent = _STYLES;
    root.appendChild(style);

    const snapshot = this._getSnapshot();
    const status = _status(snapshot);
    const paid = _is_paid(snapshot);

    const today_kwh = snapshot && snapshot.production && snapshot.production.today_kwh;
    const expected_kwh = snapshot && snapshot.expected && snapshot.expected.today_kwh;
    const shortfall_pct = snapshot && snapshot.shortfall && snapshot.shortfall.today_pct;
    const tier_label = (snapshot && snapshot.tier_label) || "Loading…";

    const BADGE_LABELS = {
      healthy: "Healthy", under: "Underperforming",
      anomaly: "Anomaly detected", unknown: "Loading…"
    };

    const card = _el("div", "ow-card");

    // Header
    const header = _el("div", "ow-header");
    header.appendChild(_el("span", "ow-title", "OwlWatt Solar"));
    header.appendChild(_el("span", "ow-badge ow-badge-" + status, BADGE_LABELS[status] || "—"));
    card.appendChild(header);

    // Stats grid
    const grid = _el("div", "ow-stats");
    const prodBlock = _el("div", "ow-stat-block");
    prodBlock.appendChild(_el("span", "ow-stat-label", "Today's Production"));
    prodBlock.appendChild(_el("span", "ow-stat-value", _fmt_kwh(today_kwh)));
    grid.appendChild(prodBlock);
    const expBlock = _el("div", "ow-stat-block");
    expBlock.appendChild(_el("span", "ow-stat-label", "Expected"));
    expBlock.appendChild(_el("span", "ow-stat-value", _fmt_kwh(expected_kwh)));
    grid.appendChild(expBlock);
    card.appendChild(grid);

    // Progress bar
    const barTrack = _el("div", "ow-bar-track");
    const barFill = _el("div", "ow-bar-fill");
    barFill.style.width = _bar_pct(today_kwh, expected_kwh).toFixed(1) + "%";
    barTrack.appendChild(barFill);
    card.appendChild(barTrack);

    // Shortfall + tier
    card.appendChild(_el("div", "ow-shortfall",
      "Shortfall today: " + _fmt_pct(shortfall_pct) + " · " + tier_label));

    // Share row (paid only) or upsell (trial only)
    if (paid) {
      const shareRow = _el("div", "ow-share-row");
      const btn = _el("button", "ow-share-btn",
        this._shareInProgress ? "Creating link…" : "Share my OwlWatt solar");
      btn.type = "button";
      if (this._shareInProgress) btn.disabled = true;
      btn.addEventListener("click", () => this._handleShare());
      shareRow.appendChild(btn);
      shareRow.appendChild(_el("span", "ow-share-tip",
        "Creates a 7-day public link. Your address is anonymized. Anyone with the link can view it."));
      card.appendChild(shareRow);
      if (this._shareError) {
        card.appendChild(_el("div", "ow-error", this._shareError));
      }
    } else if (snapshot && snapshot.tier === "trial") {
      const upsell = _el("div", "ow-upsell");
      const unlockUrl = (snapshot.claim && snapshot.claim.unlock_url)
        || "https://owlwatt.com/app/dashboard?upsell=ha";
      const link = document.createElement("a");
      link.className = "ow-upsell-link";
      link.textContent = "Upgrade to see claim value →";
      link.href = unlockUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      upsell.appendChild(link);
      card.appendChild(upsell);
    }

    root.appendChild(card);
  }

  getCardSize() {
    return 3;
  }
}

customElements.define("owlwatt-card", OwlWattCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "owlwatt-card",
  name: "OwlWatt Solar Card",
  description: "Independent solar production vs expected, shortfall status, and share button. Requires the OwlWatt integration.",
  preview: false,
  documentationURL: "https://owlwatt.com/ha",
});

console.info(
  "%c OWLWATT-CARD %c v" + OWLWATT_CARD_VERSION + " ",
  "color: #fff; background: #0ea5e9; padding: 2px 4px; border-radius: 3px;",
  "color: #0ea5e9; background: #f0f9ff; padding: 2px 4px; border-radius: 3px;"
);

"""OwlWatt API client — async aiohttp wrapper for /api/ha/v1/* endpoints."""
from __future__ import annotations

import json
import logging
from importlib.resources import files
from pathlib import Path
from typing import Any, Optional

import aiohttp

from .const import DEFAULT_API_BASE, DOMAIN

log = logging.getLogger(__name__)

# Read integration version from manifest.json at import time.
try:
    _manifest_path = Path(__file__).parent / "manifest.json"
    _INTEGRATION_VERSION = json.loads(_manifest_path.read_text())["version"]
except Exception:
    _INTEGRATION_VERSION = "0.0.0"

_USER_AGENT = f"owlwatt-ha/{_INTEGRATION_VERSION}"


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class OwlWattApiError(Exception):
    """Generic API error (non-auth, non-rate-limit)."""


class OwlWattAuthError(OwlWattApiError):
    """401 — token invalid or revoked; triggers HA reauth flow."""


class OwlWattScopeError(OwlWattApiError):
    """403 — token lacks the required scope."""


class OwlWattRateLimited(OwlWattApiError):
    """429 — rate limited by the cloud."""

    def __init__(self, retry_after_seconds: float = 60.0) -> None:
        super().__init__(f"Rate limited; retry in {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class OwlWattApiClient:
    """Async HTTP client for the OwlWatt HA integration API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str,
        base_url: str = DEFAULT_API_BASE,
    ) -> None:
        self._session = session
        self._token = token
        self._base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "User-Agent": _USER_AGENT,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
    ) -> Any:
        """Send a request; raise typed exceptions on error status codes."""
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers(),
                json=json_body,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 401:
                    raise OwlWattAuthError("Token invalid or revoked")
                if resp.status == 403:
                    raise OwlWattScopeError("Token scope insufficient")
                if resp.status == 429:
                    retry_after = float(
                        resp.headers.get("Retry-After", "60")
                    )
                    raise OwlWattRateLimited(retry_after)
                if resp.status == 204:
                    return None  # heartbeat, or no-content image responses
                if not (200 <= resp.status < 300):
                    text = await resp.text()
                    raise OwlWattApiError(
                        f"HTTP {resp.status} from {url}: {text[:200]}"
                    )
                return await resp.json()
        except (OwlWattAuthError, OwlWattScopeError, OwlWattRateLimited, OwlWattApiError):
            raise
        except aiohttp.ClientError as exc:
            raise OwlWattApiError(f"Connection error: {exc}") from exc

    async def _request_bytes(self, path: str) -> Optional[bytes]:
        """Return raw response bytes or None for 204 No Content."""
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(
                url,
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 401:
                    raise OwlWattAuthError("Token invalid or revoked")
                if resp.status == 403:
                    raise OwlWattScopeError("Token scope insufficient")
                if resp.status == 429:
                    retry_after = float(resp.headers.get("Retry-After", "60"))
                    raise OwlWattRateLimited(retry_after)
                if resp.status == 204:
                    return None
                if not (200 <= resp.status < 300):
                    text = await resp.text()
                    raise OwlWattApiError(f"HTTP {resp.status} from {url}: {text[:200]}")
                return await resp.read()
        except (OwlWattAuthError, OwlWattScopeError, OwlWattRateLimited, OwlWattApiError):
            raise
        except aiohttp.ClientError as exc:
            raise OwlWattApiError(f"Connection error: {exc}") from exc

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def get_manifest(self) -> dict:
        """GET /api/ha/v1/manifest — validate token + retrieve feature flags."""
        result = await self._request("GET", "/api/ha/v1/manifest")
        return result or {}

    async def get_snapshot(self) -> dict:
        """GET /api/ha/v1/snapshot — tier-aware live data bundle."""
        result = await self._request("GET", "/api/ha/v1/snapshot")
        return result or {}

    async def post_heartbeat(self, ha_version: str) -> None:
        """POST /api/ha/v1/heartbeat — tell cloud the HA integration is alive."""
        await self._request(
            "POST",
            "/api/ha/v1/heartbeat",
            json_body={"ha_version": ha_version},
        )

    async def get_claims(self) -> list:
        """GET /api/ha/v1/claims — list customer claims."""
        result = await self._request("GET", "/api/ha/v1/claims")
        return result if isinstance(result, list) else []

    async def get_claim(self, claim_id: int) -> dict:
        """GET /api/ha/v1/claims/{claim_id} — claim detail."""
        result = await self._request("GET", f"/api/ha/v1/claims/{claim_id}")
        return result or {}

    async def get_roof_image_bytes(self) -> Optional[bytes]:
        """GET /api/ha/v1/roof/image — latest baked roof image bytes (paid tier)."""
        return await self._request_bytes("/api/ha/v1/roof/image")

    async def get_roof_before_image_bytes(self) -> Optional[bytes]:
        """GET /api/ha/v1/roof/before — pre-install reference image bytes (paid tier)."""
        return await self._request_bytes("/api/ha/v1/roof/before")

    async def create_share_link(self) -> dict:
        """POST /api/ha/v1/share — mint a 7-day signed share URL.

        Returns {"url": "...", "token": "...", "expires_at": "..."}.
        The share URL is PUBLIC — anyone with it can view the PNG.
        No financial claim values are included in the shared image (C2).
        """
        result = await self._request("POST", "/api/ha/v1/share")
        return result if isinstance(result, dict) else {}

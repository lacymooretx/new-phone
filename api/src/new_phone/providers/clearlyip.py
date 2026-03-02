"""ClearlyIP Trunking API provider implementation."""

import time

import httpx
import structlog

from new_phone.providers.base import (
    DIDPurchaseResult,
    DIDSearchResult,
    TelephonyProvider,
    TrunkProvisionRequest,
    TrunkProvisionResult,
    TrunkTestResult,
)

logger = structlog.get_logger()

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class ClearlyIPProvider(TelephonyProvider):
    """ClearlyIP Trunking API implementation.

    Authenticates with ``X-API-Key`` header.  Base URL and key are provided
    at construction time (sourced from ``NP_CLEARLYIP_*`` env vars via config).
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _check_configured(self) -> None:
        if not self.base_url or not self.api_key:
            raise ValueError(
                "ClearlyIP provider is not configured. "
                "Set NP_CLEARLYIP_API_URL and NP_CLEARLYIP_API_KEY environment variables."
            )

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # DID operations
    # ------------------------------------------------------------------

    async def search_dids(
        self,
        area_code: str | None,
        state: str | None,
        quantity: int,
    ) -> list[DIDSearchResult]:
        self._check_configured()
        params: dict[str, str | int] = {"limit": quantity}
        if area_code:
            params["area_code"] = area_code
        if state:
            params["state"] = state

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/v1/dids/available",
                    headers=self._headers(),
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "clearlyip_search_dids_error",
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                raise
            except httpx.RequestError as exc:
                logger.error("clearlyip_search_dids_network_error", error=str(exc))
                raise

        results: list[DIDSearchResult] = []
        for item in data.get("numbers", []):
            results.append(
                DIDSearchResult(
                    number=item["number"],
                    monthly_cost=float(item.get("monthly_cost", 0)),
                    setup_cost=float(item.get("setup_cost", 0)),
                    provider="clearlyip",
                    capabilities={
                        "sms": item.get("sms_enabled", False),
                        "mms": item.get("mms_enabled", False),
                        "voice": item.get("voice_enabled", True),
                        "fax": item.get("fax_enabled", False),
                    },
                )
            )
        return results

    async def purchase_did(self, number: str) -> DIDPurchaseResult:
        self._check_configured()
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/v1/dids/order",
                    headers=self._headers(),
                    json={"number": number},
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "clearlyip_purchase_did_error",
                    number=number,
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                raise
            except httpx.RequestError as exc:
                logger.error(
                    "clearlyip_purchase_did_network_error",
                    number=number,
                    error=str(exc),
                )
                raise

        return DIDPurchaseResult(
            number=data.get("number", number),
            provider_sid=data["sid"],
            provider="clearlyip",
        )

    async def release_did(self, provider_sid: str) -> bool:
        self._check_configured()
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.delete(
                    f"{self.base_url}/v1/dids/{provider_sid}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return True
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "clearlyip_release_did_error",
                    provider_sid=provider_sid,
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                return False
            except httpx.RequestError as exc:
                logger.error(
                    "clearlyip_release_did_network_error",
                    provider_sid=provider_sid,
                    error=str(exc),
                )
                return False

    async def configure_did(self, provider_sid: str, config: dict) -> bool:
        self._check_configured()
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.put(
                    f"{self.base_url}/v1/dids/{provider_sid}/config",
                    headers=self._headers(),
                    json=config,
                )
                resp.raise_for_status()
                return True
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "clearlyip_configure_did_error",
                    provider_sid=provider_sid,
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                return False
            except httpx.RequestError as exc:
                logger.error(
                    "clearlyip_configure_did_network_error",
                    provider_sid=provider_sid,
                    error=str(exc),
                )
                return False

    # ------------------------------------------------------------------
    # Trunk operations
    # ------------------------------------------------------------------

    async def create_trunk(self, config: TrunkProvisionRequest) -> TrunkProvisionResult:
        self._check_configured()
        payload = {
            "name": config.name,
            "region": config.region,
            "channels": config.channels,
            "transport": "tls",
            **config.config,
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/v1/trunks",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "clearlyip_create_trunk_error",
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                raise
            except httpx.RequestError as exc:
                logger.error("clearlyip_create_trunk_network_error", error=str(exc))
                raise

        return TrunkProvisionResult(
            provider_trunk_id=data["trunk_id"],
            host=data["host"],
            port=int(data.get("port", 5061)),
            username=data.get("username", ""),
            password=data.get("password", ""),
        )

    async def delete_trunk(self, provider_trunk_id: str) -> bool:
        self._check_configured()
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.delete(
                    f"{self.base_url}/v1/trunks/{provider_trunk_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return True
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "clearlyip_delete_trunk_error",
                    provider_trunk_id=provider_trunk_id,
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                return False
            except httpx.RequestError as exc:
                logger.error(
                    "clearlyip_delete_trunk_network_error",
                    provider_trunk_id=provider_trunk_id,
                    error=str(exc),
                )
                return False

    async def get_trunk_status(self, provider_trunk_id: str) -> str:
        self._check_configured()
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/v1/trunks/{provider_trunk_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return str(data.get("status", "unknown"))
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "clearlyip_get_trunk_status_error",
                    provider_trunk_id=provider_trunk_id,
                    status=exc.response.status_code,
                )
                return "error"
            except httpx.RequestError as exc:
                logger.error(
                    "clearlyip_get_trunk_status_network_error",
                    provider_trunk_id=provider_trunk_id,
                    error=str(exc),
                )
                return "unreachable"

    async def test_trunk(self, provider_trunk_id: str) -> TrunkTestResult:
        self._check_configured()
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/v1/trunks/{provider_trunk_id}/test",
                    headers=self._headers(),
                )
                elapsed_ms = (time.monotonic() - start) * 1000
                resp.raise_for_status()
                data = resp.json()
                return TrunkTestResult(
                    status=data.get("status", "ok"),
                    latency_ms=data.get("latency_ms", elapsed_ms),
                    error=data.get("error"),
                )
            except httpx.HTTPStatusError as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.error(
                    "clearlyip_test_trunk_error",
                    provider_trunk_id=provider_trunk_id,
                    status=exc.response.status_code,
                )
                return TrunkTestResult(
                    status="error",
                    latency_ms=elapsed_ms,
                    error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                )
            except httpx.RequestError as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.error(
                    "clearlyip_test_trunk_network_error",
                    provider_trunk_id=provider_trunk_id,
                    error=str(exc),
                )
                return TrunkTestResult(
                    status="unreachable",
                    latency_ms=elapsed_ms,
                    error=str(exc),
                )

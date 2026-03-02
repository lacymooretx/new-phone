"""Twilio telephony provider implementation."""

import time
from base64 import b64encode

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
_API_BASE = "https://api.twilio.com/2010-04-01"
_TRUNKING_BASE = "https://trunking.twilio.com/v1"


class TwilioProvider(TelephonyProvider):
    """Twilio REST API implementation.

    Uses HTTP Basic Auth with Account SID / Auth Token.
    DID operations go through the main REST API.
    Trunk operations go through the Elastic SIP Trunking API.
    """

    def __init__(self, account_sid: str, auth_token: str) -> None:
        self.account_sid = account_sid
        self.auth_token = auth_token

    def _basic_auth(self) -> str:
        cred = b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        return f"Basic {cred}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._basic_auth(),
            "Accept": "application/json",
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
        url = f"{_API_BASE}/Accounts/{self.account_sid}/AvailablePhoneNumbers/US/Local.json"
        params: dict[str, str | int] = {"PageSize": min(quantity, 30)}
        if area_code:
            params["AreaCode"] = area_code
        if state:
            params["InRegion"] = state

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.get(url, headers=self._headers(), params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "twilio_search_dids_error",
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                raise
            except httpx.RequestError as exc:
                logger.error("twilio_search_dids_network_error", error=str(exc))
                raise

        results: list[DIDSearchResult] = []
        for item in data.get("available_phone_numbers", []):
            results.append(
                DIDSearchResult(
                    number=item["phone_number"],
                    monthly_cost=1.15,  # Twilio US local standard rate
                    setup_cost=1.00,
                    provider="twilio",
                    capabilities={
                        "sms": item.get("capabilities", {}).get("sms", False),
                        "mms": item.get("capabilities", {}).get("mms", False),
                        "voice": item.get("capabilities", {}).get("voice", True),
                        "fax": item.get("capabilities", {}).get("fax", False),
                    },
                )
            )
        return results

    async def purchase_did(self, number: str) -> DIDPurchaseResult:
        url = f"{_API_BASE}/Accounts/{self.account_sid}/IncomingPhoneNumbers.json"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._headers(),
                    data={"PhoneNumber": number},
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "twilio_purchase_did_error",
                    number=number,
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                raise
            except httpx.RequestError as exc:
                logger.error(
                    "twilio_purchase_did_network_error",
                    number=number,
                    error=str(exc),
                )
                raise

        return DIDPurchaseResult(
            number=data["phone_number"],
            provider_sid=data["sid"],
            provider="twilio",
        )

    async def release_did(self, provider_sid: str) -> bool:
        url = (
            f"{_API_BASE}/Accounts/{self.account_sid}"
            f"/IncomingPhoneNumbers/{provider_sid}.json"
        )
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.delete(url, headers=self._headers())
                resp.raise_for_status()
                return True
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "twilio_release_did_error",
                    provider_sid=provider_sid,
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                return False
            except httpx.RequestError as exc:
                logger.error(
                    "twilio_release_did_network_error",
                    provider_sid=provider_sid,
                    error=str(exc),
                )
                return False

    async def configure_did(self, provider_sid: str, config: dict) -> bool:
        url = (
            f"{_API_BASE}/Accounts/{self.account_sid}"
            f"/IncomingPhoneNumbers/{provider_sid}.json"
        )
        payload: dict[str, str] = {}
        if "voice_url" in config:
            payload["VoiceUrl"] = config["voice_url"]
        if "sms_url" in config:
            payload["SmsUrl"] = config["sms_url"]
        if "status_callback" in config:
            payload["StatusCallback"] = config["status_callback"]
        if "trunk_sid" in config:
            payload["TrunkSid"] = config["trunk_sid"]

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.post(url, headers=self._headers(), data=payload)
                resp.raise_for_status()
                return True
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "twilio_configure_did_error",
                    provider_sid=provider_sid,
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                return False
            except httpx.RequestError as exc:
                logger.error(
                    "twilio_configure_did_network_error",
                    provider_sid=provider_sid,
                    error=str(exc),
                )
                return False

    # ------------------------------------------------------------------
    # Trunk operations  (Elastic SIP Trunking API)
    # ------------------------------------------------------------------

    async def create_trunk(self, config: TrunkProvisionRequest) -> TrunkProvisionResult:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # 1. Create the trunk resource
            try:
                resp = await client.post(
                    f"{_TRUNKING_BASE}/Trunks",
                    headers=self._headers(),
                    data={
                        "FriendlyName": config.name,
                        "Secure": "true",
                    },
                )
                resp.raise_for_status()
                trunk_data = resp.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "twilio_create_trunk_error",
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                raise
            except httpx.RequestError as exc:
                logger.error("twilio_create_trunk_network_error", error=str(exc))
                raise

            trunk_sid = trunk_data["sid"]

            # 2. Create an origination URI so Twilio can reach FreeSWITCH
            origination_host = config.config.get("origination_host", "")
            origination_port = config.config.get("origination_port", 5061)
            if origination_host:
                try:
                    resp = await client.post(
                        f"{_TRUNKING_BASE}/Trunks/{trunk_sid}/OriginationUrls",
                        headers=self._headers(),
                        data={
                            "FriendlyName": f"{config.name}-origin",
                            "SipUrl": f"sip:{origination_host}:{origination_port};transport=tls",
                            "Priority": "1",
                            "Weight": "100",
                            "Enabled": "true",
                        },
                    )
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "twilio_create_origination_url_error",
                        trunk_sid=trunk_sid,
                        status=exc.response.status_code,
                        body=exc.response.text,
                    )

            # 3. Create a credential list for registration auth
            username = config.config.get("username", f"trunk-{trunk_sid[:8]}")
            password = config.config.get("password", "")
            if password:
                try:
                    # Create credential list
                    cred_resp = await client.post(
                        f"{_API_BASE}/Accounts/{self.account_sid}/SIP/CredentialLists.json",
                        headers=self._headers(),
                        data={"FriendlyName": f"{config.name}-creds"},
                    )
                    cred_resp.raise_for_status()
                    cred_list_sid = cred_resp.json()["sid"]

                    # Add credential
                    await client.post(
                        f"{_API_BASE}/Accounts/{self.account_sid}"
                        f"/SIP/CredentialLists/{cred_list_sid}/Credentials.json",
                        headers=self._headers(),
                        data={"Username": username, "Password": password},
                    )

                    # Associate credential list with trunk
                    await client.post(
                        f"{_TRUNKING_BASE}/Trunks/{trunk_sid}/CredentialLists",
                        headers=self._headers(),
                        data={"CredentialListSid": cred_list_sid},
                    )
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "twilio_create_credentials_error",
                        trunk_sid=trunk_sid,
                        status=exc.response.status_code,
                    )

        # Twilio Elastic SIP Trunking termination URI
        termination_host = f"{trunk_sid}.pstn.twilio.com"
        return TrunkProvisionResult(
            provider_trunk_id=trunk_sid,
            host=termination_host,
            port=5061,
            username=username,
            password=password,
        )

    async def delete_trunk(self, provider_trunk_id: str) -> bool:
        url = f"{_TRUNKING_BASE}/Trunks/{provider_trunk_id}"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.delete(url, headers=self._headers())
                resp.raise_for_status()
                return True
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "twilio_delete_trunk_error",
                    provider_trunk_id=provider_trunk_id,
                    status=exc.response.status_code,
                    body=exc.response.text,
                )
                return False
            except httpx.RequestError as exc:
                logger.error(
                    "twilio_delete_trunk_network_error",
                    provider_trunk_id=provider_trunk_id,
                    error=str(exc),
                )
                return False

    async def get_trunk_status(self, provider_trunk_id: str) -> str:
        url = f"{_TRUNKING_BASE}/Trunks/{provider_trunk_id}"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                # Twilio doesn't have a direct "status" — infer from response
                if data.get("sid"):
                    return "active"
                return "unknown"
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "twilio_get_trunk_status_error",
                    provider_trunk_id=provider_trunk_id,
                    status=exc.response.status_code,
                )
                if exc.response.status_code == 404:
                    return "not_found"
                return "error"
            except httpx.RequestError as exc:
                logger.error(
                    "twilio_get_trunk_status_network_error",
                    provider_trunk_id=provider_trunk_id,
                    error=str(exc),
                )
                return "unreachable"

    async def test_trunk(self, provider_trunk_id: str) -> TrunkTestResult:
        """Test trunk connectivity by fetching its status from Twilio."""
        start = time.monotonic()
        url = f"{_TRUNKING_BASE}/Trunks/{provider_trunk_id}"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.get(url, headers=self._headers())
                elapsed_ms = (time.monotonic() - start) * 1000
                resp.raise_for_status()
                return TrunkTestResult(
                    status="ok",
                    latency_ms=elapsed_ms,
                    error=None,
                )
            except httpx.HTTPStatusError as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.error(
                    "twilio_test_trunk_error",
                    provider_trunk_id=provider_trunk_id,
                    status=exc.response.status_code,
                )
                return TrunkTestResult(
                    status="error",
                    latency_ms=elapsed_ms,
                    error=f"HTTP {exc.response.status_code}",
                )
            except httpx.RequestError as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.error(
                    "twilio_test_trunk_network_error",
                    provider_trunk_id=provider_trunk_id,
                    error=str(exc),
                )
                return TrunkTestResult(
                    status="unreachable",
                    latency_ms=elapsed_ms,
                    error=str(exc),
                )

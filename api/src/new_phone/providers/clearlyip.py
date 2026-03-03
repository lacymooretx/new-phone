"""ClearlyIP keycode-based provider implementation.

ClearlyIP uses a keycode (per-location bearer token) model:
  1. Customer creates a "location" in the ClearlyIP portal -> auto-generates a keycode
  2. GET https://unity.clearlyip.com/trunking/v1/location  with  X-Token: {keycode}
  3. Returns full SIP config: username, password, server addresses, assigned DIDs
  4. DID management happens in the ClearlyIP portal only — no API for search/purchase/release
  5. The same keycode authenticates SMS API (sms.clearlyip.com) and Fax API (fax.sendfax.to)
"""

import httpx
import structlog

from new_phone.providers.base import ClearlyIPLocationConfig, KeycodeActivationProvider

logger = structlog.get_logger()

UNITY_BASE_URL = "https://unity.clearlyip.com/trunking/v1"
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class ClearlyIPProvider(KeycodeActivationProvider):
    """ClearlyIP keycode-based provider.

    Does NOT implement :class:`TelephonyProvider` — ClearlyIP has no CRUD
    API for trunks/DIDs.  All provisioning is keycode-based.
    """

    async def fetch_location_config(self, keycode: str) -> ClearlyIPLocationConfig:
        """Call the Unity API to retrieve full location SIP config."""
        if not keycode:
            raise ValueError("ClearlyIP keycode is required")

        headers = {
            "X-Token": keycode,
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.get(
                    f"{UNITY_BASE_URL}/location",
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "clearlyip_fetch_location_error",
                    status=exc.response.status_code,
                    body=exc.response.text[:500],
                )
                if exc.response.status_code == 401:
                    raise ValueError("Invalid or expired ClearlyIP keycode") from exc
                raise
            except httpx.RequestError as exc:
                logger.error(
                    "clearlyip_fetch_location_network_error",
                    error=str(exc),
                )
                raise

        # Log raw response for debugging — exact field names may need
        # real-world validation since they are inferred from FreePBX module
        logger.info(
            "clearlyip_raw_response",
            keys=list(data.keys()) if isinstance(data, dict) else "non-dict",
        )

        return self._parse_location_response(data)

    async def validate_keycode(self, keycode: str) -> bool:
        """Lightweight check — just verify we get a 200 from Unity."""
        if not keycode:
            return False

        headers = {
            "X-Token": keycode,
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                resp = await client.get(
                    f"{UNITY_BASE_URL}/location",
                    headers=headers,
                )
                return resp.status_code == 200
            except httpx.RequestError:
                return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_location_response(data: dict) -> ClearlyIPLocationConfig:
        """Parse the Unity API response into our dataclass.

        Field names are inferred from the FreePBX ClearlyIP module behaviour.
        We access them flexibly and fall back to sensible defaults.
        """
        # Try multiple possible field names for each value
        def _get(keys: list[str], default: object = "") -> object:
            for k in keys:
                if k in data and data[k] is not None:
                    return data[k]
            return default

        location_name = str(_get(["location_name", "name", "locationName"], "ClearlyIP Location"))
        sip_username = str(_get(["username", "sip_username", "sipUsername"], ""))
        sip_password = str(_get(["password", "sip_password", "sipPassword"], ""))
        primary_server = str(_get(["primary_server", "server", "primaryServer", "host"], ""))
        secondary_server = str(_get(["secondary_server", "secondaryServer", "backup_server", "backupServer"], ""))
        primary_port = int(_get(["primary_port", "port", "primaryPort"], 5061))
        secondary_port = int(_get(["secondary_port", "secondaryPort", "backup_port"], 5061))

        # DIDs can be a list of strings, list of dicts, or a single string
        raw_dids = _get(["dids", "numbers", "assigned_numbers", "assignedNumbers"], [])
        dids: list[str] = []
        if isinstance(raw_dids, list):
            for d in raw_dids:
                if isinstance(d, str):
                    dids.append(d)
                elif isinstance(d, dict):
                    dids.append(str(d.get("number", d.get("did", ""))))
        elif isinstance(raw_dids, str):
            dids = [raw_dids] if raw_dids else []

        # E911 config (optional)
        e911_config = _get(["e911", "e911_config", "e911Config"], {})
        if not isinstance(e911_config, dict):
            e911_config = {}

        return ClearlyIPLocationConfig(
            location_name=location_name,
            sip_username=sip_username,
            sip_password=sip_password,
            primary_server=primary_server,
            secondary_server=secondary_server,
            primary_port=primary_port,
            secondary_port=secondary_port,
            dids=dids,
            e911_config=e911_config,
            raw_response=data,
        )

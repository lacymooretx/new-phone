"""Zoho CRM provider — contact search via v2 API."""

import structlog
from httpx import AsyncClient

from new_phone.integrations.crm.provider_base import CRMContact, CRMProviderBase

logger = structlog.get_logger()


class ZohoProvider(CRMProviderBase):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        api_domain: str | None = None,
        base_url: str | None = None,
        timeout: int = 5,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.api_domain = api_domain or "https://www.zohoapis.com"
        self.accounts_url = base_url or "https://accounts.zoho.com"
        self.timeout = timeout
        self._access_token: str | None = None

    async def _authenticate(self, client: AsyncClient) -> None:
        """Refresh the OAuth access token."""
        resp = await client.post(
            f"{self.accounts_url}/oauth/v2/token",
            params={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
            },
        )
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Zoho-oauthtoken {self._access_token}"}

    def _strip_phone(self, phone: str) -> str:
        return "".join(c for c in phone if c.isdigit())[-10:]

    async def lookup_by_phone(self, phone: str) -> CRMContact | None:
        digits = self._strip_phone(phone)
        if len(digits) < 7:
            return None

        async with AsyncClient(timeout=self.timeout) as client:
            if not self._access_token:
                await self._authenticate(client)

            resp = await client.get(
                f"{self.api_domain}/crm/v2/Contacts/search",
                headers=self._headers(),
                params={"phone": digits},
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])

            if not data:
                return None

            rec = data[0]
            contact_id = str(rec.get("id", ""))
            first = rec.get("First_Name", "")
            last = rec.get("Last_Name", "")
            account = rec.get("Account_Name", {})
            account_name = account.get("name", "") if isinstance(account, dict) else str(account)

            return CRMContact(
                customer_name=f"{first} {last}".strip(),
                company_name=account_name,
                contact_id=contact_id,
                deep_link_url=(
                    f"{self.api_domain.replace('zohoapis', 'zoho')}/crm/tab/Contacts/{contact_id}"
                    if contact_id
                    else ""
                ),
            )

    async def test_connection(self) -> dict:
        try:
            async with AsyncClient(timeout=self.timeout) as client:
                await self._authenticate(client)
                resp = await client.get(
                    f"{self.api_domain}/crm/v2/org",
                    headers=self._headers(),
                )
                resp.raise_for_status()
            return {"success": True, "message": "Zoho CRM connection successful"}
        except Exception as e:
            logger.warning("zoho_test_failed", error=str(e))
            return {"success": False, "message": f"Zoho CRM connection failed: {e}"}

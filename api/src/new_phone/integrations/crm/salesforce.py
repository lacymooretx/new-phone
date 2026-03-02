"""Salesforce CRM provider — contact lookup via REST API + SOQL."""

import structlog
from httpx import AsyncClient

from new_phone.integrations.crm.provider_base import CRMContact, CRMProviderBase

logger = structlog.get_logger()


class SalesforceProvider(CRMProviderBase):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        security_token: str,
        base_url: str | None = None,
        timeout: int = 5,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.security_token = security_token
        self.login_url = base_url or "https://login.salesforce.com"
        self.timeout = timeout
        self._instance_url: str | None = None
        self._access_token: str | None = None

    async def _authenticate(self, client: AsyncClient) -> None:
        """Obtain OAuth token via username-password flow."""
        resp = await client.post(
            f"{self.login_url}/services/oauth2/token",
            data={
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": f"{self.password}{self.security_token}",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._instance_url = data["instance_url"]

    def _strip_phone(self, phone: str) -> str:
        """Strip non-digit chars for SOQL LIKE matching."""
        return "".join(c for c in phone if c.isdigit())[-10:]

    async def lookup_by_phone(self, phone: str) -> CRMContact | None:
        digits = self._strip_phone(phone)
        if len(digits) < 7:
            return None

        async with AsyncClient(timeout=self.timeout) as client:
            if not self._access_token:
                await self._authenticate(client)

            soql = (
                "SELECT Id, Name, Phone, Account.Name, Account.AccountNumber, "
                "Account.Type "
                f"FROM Contact WHERE Phone LIKE '%{digits}' "
                "OR MobilePhone LIKE '%{digits}' "
                "OR HomePhone LIKE '%{digits}' "
                "LIMIT 1"
            ).replace("{digits}", digits)

            resp = await client.get(
                f"{self._instance_url}/services/data/v59.0/query",
                params={"q": soql},
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            resp.raise_for_status()
            records = resp.json().get("records", [])

            if not records:
                return None

            rec = records[0]
            account = rec.get("Account") or {}
            contact_id = rec.get("Id", "")
            return CRMContact(
                customer_name=rec.get("Name", ""),
                company_name=account.get("Name", ""),
                account_number=account.get("AccountNumber", ""),
                account_status=account.get("Type", ""),
                contact_id=contact_id,
                deep_link_url=f"{self._instance_url}/{contact_id}" if contact_id else "",
            )

    async def test_connection(self) -> dict:
        try:
            async with AsyncClient(timeout=self.timeout) as client:
                await self._authenticate(client)
                resp = await client.get(
                    f"{self._instance_url}/services/data/v59.0/limits",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
                resp.raise_for_status()
            return {"success": True, "message": "Salesforce connection successful"}
        except Exception as e:
            logger.warning("salesforce_test_failed", error=str(e))
            return {"success": False, "message": f"Salesforce connection failed: {e}"}

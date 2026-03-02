"""ConnectWise Manage CRM provider — contact/company lookup."""

import base64

import structlog
from httpx import AsyncClient

from new_phone.integrations.crm.provider_base import CRMContact, CRMProviderBase

logger = structlog.get_logger()


class ConnectWiseCRMProvider(CRMProviderBase):
    def __init__(
        self,
        company_id: str,
        public_key: str,
        private_key: str,
        client_id: str,
        base_url: str | None = None,
        timeout: int = 5,
    ):
        self.company_id = company_id
        self.public_key = public_key
        self.private_key = private_key
        self.client_id = client_id
        self.base_url = (base_url or "https://na.myconnectwise.net").rstrip("/")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        creds = f"{self.company_id}+{self.public_key}:{self.private_key}"
        encoded = base64.b64encode(creds.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "clientId": self.client_id,
            "Content-Type": "application/json",
        }

    def _strip_phone(self, phone: str) -> str:
        return "".join(c for c in phone if c.isdigit())[-10:]

    async def lookup_by_phone(self, phone: str) -> CRMContact | None:
        digits = self._strip_phone(phone)
        if len(digits) < 7:
            return None

        async with AsyncClient(timeout=self.timeout) as client:
            # Search contacts by phone
            resp = await client.get(
                f"{self.base_url}/v4_6_release/apis/3.0/company/contacts",
                headers=self._headers(),
                params={
                    "conditions": (
                        f"communicationItems/value like '%{digits}' "
                        f"AND communicationItems/communicationType = 'Phone'"
                    ),
                    "pageSize": 1,
                    "fields": "id,firstName,lastName,company",
                },
            )
            resp.raise_for_status()
            contacts = resp.json()

            if not contacts:
                return None

            contact = contacts[0]
            contact_id = str(contact.get("id", ""))
            first = contact.get("firstName", "")
            last = contact.get("lastName", "")
            company = contact.get("company", {})
            company_name = company.get("name", "") if isinstance(company, dict) else ""
            company_id = str(company.get("id", "")) if isinstance(company, dict) else ""

            return CRMContact(
                customer_name=f"{first} {last}".strip(),
                company_name=company_name,
                contact_id=contact_id,
                account_number=company_id,
                deep_link_url=(
                    f"{self.base_url}/v4_6_release/ConnectWise.aspx"
                    f"?locale=en_US&contactRec={contact_id}"
                    if contact_id
                    else ""
                ),
            )

    async def test_connection(self) -> dict:
        try:
            async with AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/v4_6_release/apis/3.0/system/info",
                    headers=self._headers(),
                )
                resp.raise_for_status()
            return {"success": True, "message": "ConnectWise connection successful"}
        except Exception as e:
            logger.warning("connectwise_crm_test_failed", error=str(e))
            return {"success": False, "message": f"ConnectWise connection failed: {e}"}

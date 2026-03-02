"""HubSpot CRM provider — contact search via v3 API."""

import httpx
import structlog

from new_phone.integrations.crm.provider_base import (
    CRMContact,
    CRMProviderBase,
    create_crm_client,
    crm_retry,
)

logger = structlog.get_logger()

HUBSPOT_API = "https://api.hubapi.com"


class HubSpotProvider(CRMProviderBase):
    def __init__(self, access_token: str, base_url: str | None = None):
        self.access_token = access_token
        self.api_url = base_url or HUBSPOT_API

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _strip_phone(self, phone: str) -> str:
        return "".join(c for c in phone if c.isdigit())[-10:]

    async def lookup_by_phone(self, phone: str) -> CRMContact | None:
        digits = self._strip_phone(phone)
        if len(digits) < 7:
            return None

        try:
            async with create_crm_client() as client:
                search_body = {
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "phone",
                                    "operator": "CONTAINS_TOKEN",
                                    "value": f"*{digits}",
                                }
                            ]
                        },
                        {
                            "filters": [
                                {
                                    "propertyName": "mobilephone",
                                    "operator": "CONTAINS_TOKEN",
                                    "value": f"*{digits}",
                                }
                            ]
                        },
                    ],
                    "properties": [
                        "firstname",
                        "lastname",
                        "phone",
                        "company",
                        "hs_object_id",
                    ],
                    "limit": 1,
                }

                async def _do_search():
                    resp = await client.post(
                        f"{self.api_url}/crm/v3/objects/contacts/search",
                        headers=self._headers(),
                        json=search_body,
                    )
                    resp.raise_for_status()
                    return resp.json().get("results", [])

                results = await crm_retry(_do_search, provider_name="hubspot")

                if not results:
                    return None

                props = results[0].get("properties", {})
                contact_id = results[0].get("id", "")
                first = props.get("firstname", "")
                last = props.get("lastname", "")
                full_name = f"{first} {last}".strip()

                return CRMContact(
                    customer_name=full_name,
                    company_name=props.get("company", ""),
                    contact_id=contact_id,
                    deep_link_url=(
                        f"https://app.hubspot.com/contacts/{contact_id}" if contact_id else ""
                    ),
                )
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("hubspot_lookup_failed", phone=phone, error=str(exc))
            return None
        except Exception as exc:
            logger.warning("hubspot_lookup_unexpected_error", phone=phone, error=str(exc))
            return None

    async def test_connection(self) -> dict:
        try:
            async with create_crm_client() as client:
                resp = await client.get(
                    f"{self.api_url}/crm/v3/objects/contacts",
                    headers=self._headers(),
                    params={"limit": 1},
                )
                resp.raise_for_status()
            return {"success": True, "message": "HubSpot connection successful"}
        except Exception as e:
            logger.warning("hubspot_test_failed", error=str(e))
            return {"success": False, "message": f"HubSpot connection failed: {e}"}

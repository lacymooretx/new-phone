"""Custom webhook CRM provider — POST phone number, get contact back."""

import httpx
import structlog

from new_phone.integrations.crm.provider_base import (
    CRMContact,
    CRMProviderBase,
    create_crm_client,
    crm_retry,
)

logger = structlog.get_logger()


class WebhookProvider(CRMProviderBase):
    def __init__(self, url: str, auth_header: str = ""):
        self.url = url
        self.auth_header = auth_header

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.auth_header:
            headers["Authorization"] = self.auth_header
        return headers

    async def lookup_by_phone(self, phone: str) -> CRMContact | None:
        try:
            async with create_crm_client() as client:

                async def _do_lookup():
                    resp = await client.post(
                        self.url,
                        headers=self._headers(),
                        json={"phone_number": phone},
                    )
                    resp.raise_for_status()
                    return resp.json()

                data = await crm_retry(_do_lookup, provider_name="webhook")

                if not data or not data.get("customer_name"):
                    return None

                return CRMContact(
                    customer_name=data.get("customer_name", ""),
                    company_name=data.get("company_name", ""),
                    account_number=data.get("account_number", ""),
                    account_status=data.get("account_status", ""),
                    contact_id=data.get("contact_id", ""),
                    deep_link_url=data.get("deep_link_url", ""),
                    custom_fields=data.get("custom_fields", {}),
                )
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("webhook_lookup_failed", phone=phone, error=str(exc))
            return None
        except Exception as exc:
            logger.warning("webhook_lookup_unexpected_error", phone=phone, error=str(exc))
            return None

    async def test_connection(self) -> dict:
        try:
            async with create_crm_client() as client:
                resp = await client.post(
                    self.url,
                    headers=self._headers(),
                    json={"phone_number": "+10000000000", "test": True},
                )
                resp.raise_for_status()
            return {"success": True, "message": "Webhook endpoint reachable"}
        except Exception as e:
            logger.warning("webhook_test_failed", error=str(e))
            return {"success": False, "message": f"Webhook connection failed: {e}"}

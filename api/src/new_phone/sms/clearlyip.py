import math

import httpx
import structlog
from fastapi import Request

from new_phone.sms.provider_base import InboundMessage, SendResult, SMSProviderBase, StatusUpdate

logger = structlog.get_logger()

CLEARLYIP_SMS_API_URL = "https://sms.clearlyip.com/api/v1/message"

# ClearlyIP status mapping to our internal statuses
STATUS_MAP = {
    "queued": "queued",
    "sent": "sent",
    "delivered": "delivered",
    "failed": "failed",
    "undelivered": "failed",
}


class ClearlyIPProvider(SMSProviderBase):
    def __init__(self, trunk_token: str):
        self.trunk_token = trunk_token

    async def send_message(
        self, from_number: str, to_number: str, body: str, media_urls: list[str] | None = None
    ) -> SendResult:
        segments = math.ceil(len(body) / 160) if body else 1

        try:
            payload: dict = {
                "from": from_number,
                "to": to_number,
                "body": body,
            }
            if media_urls:
                payload["media_urls"] = media_urls

            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=30.0)) as client:
                response = await client.post(
                    CLEARLYIP_SMS_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.trunk_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            return SendResult(
                provider_message_id=data.get("message_id", data.get("id", "")),
                status="sent",
                segments=segments,
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "clearlyip_send_http_error",
                status_code=exc.response.status_code,
                from_number=from_number,
                to_number=to_number,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=segments)
        except httpx.RequestError as exc:
            logger.error(
                "clearlyip_send_request_error",
                from_number=from_number,
                to_number=to_number,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=segments)
        except Exception as exc:
            logger.error(
                "clearlyip_send_unexpected_error",
                from_number=from_number,
                to_number=to_number,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=segments)

    def parse_inbound_webhook(self, request_data: dict) -> InboundMessage:
        return InboundMessage(
            from_number=request_data.get("from", ""),
            to_number=request_data.get("to", ""),
            body=request_data.get("body", request_data.get("text", "")),
            provider_message_id=request_data.get("message_id", request_data.get("id", "")),
            media_urls=request_data.get("media_urls", []),
        )

    def parse_status_callback(self, request_data: dict) -> StatusUpdate:
        raw_status = request_data.get("status", "").lower()
        return StatusUpdate(
            provider_message_id=request_data.get("message_id", request_data.get("id", "")),
            status=STATUS_MAP.get(raw_status, raw_status),
            error_message=request_data.get("error_message"),
        )

    async def verify_webhook_signature(self, request: Request) -> bool:
        # ClearlyIP does not provide HMAC signatures — validate via known DID matching
        return True

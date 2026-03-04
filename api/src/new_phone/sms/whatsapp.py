import hashlib
import hmac
from datetime import UTC, datetime

import httpx
import structlog
from fastapi import Request

from new_phone.sms.provider_base import InboundMessage, SendResult, SMSProviderBase, StatusUpdate

logger = structlog.get_logger()

# WhatsApp Cloud API status mapping
STATUS_MAP = {
    "sent": "sent",
    "delivered": "delivered",
    "read": "delivered",
    "failed": "failed",
}

# WhatsApp enforces a 24-hour messaging window for session messages.
# After 24h since the last user message, only template messages are allowed.
MESSAGING_WINDOW_HOURS = 24


class WhatsAppProvider(SMSProviderBase):
    """WhatsApp Cloud API provider via Meta Graph API."""

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        app_secret: str,
        waba_id: str | None = None,
    ):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.app_secret = app_secret
        self.waba_id = waba_id

    def _is_within_messaging_window(self, last_inbound_at: datetime | None) -> bool:
        """Check if we are within the 24-hour messaging window."""
        if last_inbound_at is None:
            return False
        elapsed = datetime.now(tz=UTC) - last_inbound_at
        return elapsed.total_seconds() < MESSAGING_WINDOW_HOURS * 3600

    async def send_message(
        self,
        from_number: str,
        to_number: str,
        body: str,
        media_urls: list[str] | None = None,
    ) -> SendResult:
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # Build message payload
        if media_urls:
            # Send first media as image message with caption
            payload: dict = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "image",
                "image": {
                    "link": media_urls[0],
                    "caption": body,
                },
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": body},
            }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=30.0)) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            message_id = data.get("messages", [{}])[0].get("id", "")
            return SendResult(
                provider_message_id=message_id,
                status="sent",
                segments=1,
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "whatsapp_send_http_error",
                status_code=exc.response.status_code,
                to_number=to_number,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=1)
        except httpx.RequestError as exc:
            logger.error(
                "whatsapp_send_request_error",
                to_number=to_number,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=1)

    def parse_inbound_webhook(self, request_data: dict) -> InboundMessage:
        """Parse a WhatsApp Cloud API inbound webhook payload."""
        entry = request_data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [{}])
        message = messages[0] if messages else {}
        metadata = value.get("metadata", {})

        body = ""
        media_urls: list[str] = []
        msg_type = message.get("type", "text")

        if msg_type == "text":
            body = message.get("text", {}).get("body", "")
        elif msg_type in ("image", "video", "audio", "document"):
            media_info = message.get(msg_type, {})
            body = media_info.get("caption", "")
            # Media URL must be fetched separately via Graph API using the media ID
            media_id = media_info.get("id")
            if media_id:
                media_urls.append(f"{self.BASE_URL}/{media_id}")

        return InboundMessage(
            from_number=message.get("from", ""),
            to_number=metadata.get("display_phone_number", ""),
            body=body,
            provider_message_id=message.get("id", ""),
            media_urls=media_urls,
        )

    def parse_status_callback(self, request_data: dict) -> StatusUpdate:
        """Parse a WhatsApp Cloud API status update webhook."""
        entry = request_data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        statuses = value.get("statuses", [{}])
        status_obj = statuses[0] if statuses else {}

        raw_status = status_obj.get("status", "")
        errors = status_obj.get("errors", [])
        error_message = None
        if errors:
            err = errors[0]
            error_message = f"[{err.get('code', '')}] {err.get('title', 'Unknown error')}"

        return StatusUpdate(
            provider_message_id=status_obj.get("id", ""),
            status=STATUS_MAP.get(raw_status, raw_status),
            error_message=error_message,
        )

    async def verify_webhook_signature(self, request: Request) -> bool:
        """Verify the X-Hub-Signature-256 HMAC-SHA256 signature from Meta."""
        signature_header = request.headers.get("X-Hub-Signature-256", "")
        if not signature_header or not signature_header.startswith("sha256="):
            logger.warning("whatsapp_webhook_missing_signature")
            return False

        expected_signature = signature_header[7:]  # Strip "sha256=" prefix
        body = await request.body()

        computed = hmac.new(
            self.app_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed, expected_signature)

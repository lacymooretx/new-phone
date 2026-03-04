import hashlib
import hmac

import httpx
import structlog
from fastapi import Request

from new_phone.sms.provider_base import InboundMessage, SendResult, SMSProviderBase, StatusUpdate

logger = structlog.get_logger()

# Messenger delivery status mapping
STATUS_MAP = {
    "sent": "sent",
    "delivered": "delivered",
    "read": "delivered",
    "failed": "failed",
}


class FacebookMessengerProvider(SMSProviderBase):
    """Facebook Page Messaging API provider."""

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self, page_access_token: str, app_secret: str):
        self.page_access_token = page_access_token
        self.app_secret = app_secret

    async def send_message(
        self,
        from_number: str,
        to_number: str,
        body: str,
        media_urls: list[str] | None = None,
    ) -> SendResult:
        """Send a message via Facebook Messenger.

        Note: from_number is unused (messages come from the page).
        to_number is treated as the recipient PSID.
        """
        url = f"{self.BASE_URL}/me/messages"
        headers = {
            "Content-Type": "application/json",
        }
        params = {"access_token": self.page_access_token}

        # Build message payload
        if media_urls:
            # Send first media as attachment
            message_payload: dict = {
                "attachment": {
                    "type": "image",
                    "payload": {"url": media_urls[0], "is_reusable": True},
                }
            }
            # If there's also text, we send the attachment and note the body is in caption
            if body:
                # Messenger doesn't support caption on attachments; send text first
                # For simplicity, include text in a quick_reply-style approach
                message_payload["text"] = body
                message_payload.pop("attachment")
        else:
            message_payload = {"text": body}

        payload = {
            "recipient": {"id": to_number},
            "message": message_payload,
            "messaging_type": "RESPONSE",
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=30.0)) as client:
                response = await client.post(url, headers=headers, params=params, json=payload)
                response.raise_for_status()
                data = response.json()

            return SendResult(
                provider_message_id=data.get("message_id", ""),
                status="sent",
                segments=1,
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "messenger_send_http_error",
                status_code=exc.response.status_code,
                recipient_id=to_number,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=1)
        except httpx.RequestError as exc:
            logger.error(
                "messenger_send_request_error",
                recipient_id=to_number,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=1)

    def parse_inbound_webhook(self, request_data: dict) -> InboundMessage:
        """Parse a Facebook Messenger webhook payload."""
        entry = request_data.get("entry", [{}])[0]
        messaging = entry.get("messaging", [{}])
        event = messaging[0] if messaging else {}

        sender_id = event.get("sender", {}).get("id", "")
        recipient_id = event.get("recipient", {}).get("id", "")
        message = event.get("message", {})

        body = message.get("text", "")
        media_urls: list[str] = []

        # Handle attachments
        for attachment in message.get("attachments", []):
            payload = attachment.get("payload", {})
            url = payload.get("url")
            if url:
                media_urls.append(url)

        return InboundMessage(
            from_number=sender_id,
            to_number=recipient_id,
            body=body,
            provider_message_id=message.get("mid", ""),
            media_urls=media_urls,
        )

    def parse_status_callback(self, request_data: dict) -> StatusUpdate:
        """Parse a Messenger delivery/read receipt."""
        entry = request_data.get("entry", [{}])[0]
        messaging = entry.get("messaging", [{}])
        event = messaging[0] if messaging else {}

        # Determine status from event type
        if "delivery" in event:
            delivery = event["delivery"]
            mids = delivery.get("mids", [])
            return StatusUpdate(
                provider_message_id=mids[0] if mids else "",
                status="delivered",
            )
        if "read" in event:
            return StatusUpdate(
                provider_message_id="",
                status="delivered",
            )

        return StatusUpdate(
            provider_message_id="",
            status="sent",
        )

    async def verify_webhook_signature(self, request: Request) -> bool:
        """Verify the X-Hub-Signature-256 HMAC-SHA256 signature from Meta."""
        signature_header = request.headers.get("X-Hub-Signature-256", "")
        if not signature_header or not signature_header.startswith("sha256="):
            logger.warning("messenger_webhook_missing_signature")
            return False

        expected_signature = signature_header[7:]  # Strip "sha256=" prefix
        body = await request.body()

        computed = hmac.new(
            self.app_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed, expected_signature)

import base64
import hashlib
import hmac
import math
from urllib.parse import unquote_plus

import httpx
import structlog
from fastapi import Request

from new_phone.sms.provider_base import InboundMessage, SendResult, SMSProviderBase, StatusUpdate

logger = structlog.get_logger()

# Twilio status mapping to our internal statuses
STATUS_MAP = {
    "queued": "queued",
    "sent": "sent",
    "delivered": "delivered",
    "failed": "failed",
    "undelivered": "failed",
    "accepted": "queued",
    "sending": "sent",
}


class TwilioProvider(SMSProviderBase):
    def __init__(self, account_sid: str, auth_token: str):
        self.account_sid = account_sid
        self.auth_token = auth_token

    async def send_message(
        self, from_number: str, to_number: str, body: str, media_urls: list[str] | None = None
    ) -> SendResult:
        segments = math.ceil(len(body) / 160) if body else 1
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

        try:
            form_data: list[tuple[str, str]] = [
                ("From", from_number),
                ("To", to_number),
                ("Body", body),
            ]
            if media_urls:
                for media_url in media_urls:
                    form_data.append(("MediaUrl", media_url))

            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=30.0)) as client:
                response = await client.post(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    data=form_data,
                )
                response.raise_for_status()
                data = response.json()

            return SendResult(
                provider_message_id=data.get("sid", ""),
                status=STATUS_MAP.get(data.get("status", ""), "queued"),
                segments=data.get("num_segments", segments),
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "twilio_send_http_error",
                status_code=exc.response.status_code,
                from_number=from_number,
                to_number=to_number,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=segments)
        except httpx.RequestError as exc:
            logger.error(
                "twilio_send_request_error",
                from_number=from_number,
                to_number=to_number,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=segments)
        except Exception as exc:
            logger.error(
                "twilio_send_unexpected_error",
                from_number=from_number,
                to_number=to_number,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=segments)

    def parse_inbound_webhook(self, request_data: dict) -> InboundMessage:
        media_urls = []
        num_media = int(request_data.get("NumMedia", "0"))
        for i in range(num_media):
            url = request_data.get(f"MediaUrl{i}")
            if url:
                media_urls.append(url)

        return InboundMessage(
            from_number=request_data.get("From", ""),
            to_number=request_data.get("To", ""),
            body=request_data.get("Body", ""),
            provider_message_id=request_data.get("MessageSid", request_data.get("SmsSid", "")),
            media_urls=media_urls,
        )

    def parse_status_callback(self, request_data: dict) -> StatusUpdate:
        raw_status = request_data.get("MessageStatus", request_data.get("SmsStatus", "")).lower()
        error_code = request_data.get("ErrorCode")
        error_message = request_data.get("ErrorMessage")

        if error_code and error_code != "0":
            error_message = f"[{error_code}] {error_message or 'Unknown error'}"

        return StatusUpdate(
            provider_message_id=request_data.get("MessageSid", request_data.get("SmsSid", "")),
            status=STATUS_MAP.get(raw_status, raw_status),
            error_message=error_message,
        )

    async def verify_webhook_signature(self, request: Request) -> bool:
        """Verify Twilio X-Twilio-Signature HMAC-SHA1 validation."""
        signature = request.headers.get("X-Twilio-Signature", "")
        if not signature:
            logger.warning("twilio_webhook_missing_signature")
            return False

        # Reconstruct the full URL
        url = str(request.url)

        # Get POST params sorted
        body = await request.body()
        try:
            form_data = dict(x.split("=", 1) for x in body.decode().split("&") if "=" in x)
        except Exception:
            form_data = {}

        # Build validation string: URL + sorted POST params
        data_string = url
        for key in sorted(form_data.keys()):
            data_string += key + unquote_plus(form_data[key])

        # Compute HMAC-SHA1
        computed = hmac.new(
            self.auth_token.encode("utf-8"),
            data_string.encode("utf-8"),
            hashlib.sha1,
        ).digest()

        expected = base64.b64encode(computed).decode("utf-8")

        return hmac.compare_digest(expected, signature)

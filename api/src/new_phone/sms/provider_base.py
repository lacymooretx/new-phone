from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

from fastapi import Request


@dataclass
class SendResult:
    provider_message_id: str
    status: str
    segments: int = 1
    cost: Decimal | None = None


@dataclass
class InboundMessage:
    from_number: str
    to_number: str
    body: str
    provider_message_id: str
    media_urls: list[str] = field(default_factory=list)


@dataclass
class StatusUpdate:
    provider_message_id: str
    status: str
    error_message: str | None = None


class SMSProviderBase(ABC):
    @abstractmethod
    async def send_message(
        self, from_number: str, to_number: str, body: str, media_urls: list[str] | None = None
    ) -> SendResult:
        """Send an SMS/MMS message via this provider."""

    @abstractmethod
    def parse_inbound_webhook(self, request_data: dict) -> InboundMessage:
        """Parse an inbound SMS webhook payload into a normalized InboundMessage."""

    @abstractmethod
    def parse_status_callback(self, request_data: dict) -> StatusUpdate:
        """Parse a delivery status callback into a normalized StatusUpdate."""

    @abstractmethod
    async def verify_webhook_signature(self, request: Request) -> bool:
        """Verify the webhook signature from the provider. Returns True if valid."""

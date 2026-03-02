"""Base class and data types for CRM provider integrations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CRMContact:
    """Normalized contact result from any CRM provider."""

    customer_name: str
    company_name: str = ""
    account_number: str = ""
    account_status: str = ""
    contact_id: str = ""
    deep_link_url: str = ""
    custom_fields: dict = field(default_factory=dict)


class CRMProviderBase(ABC):
    """Abstract base class for CRM provider integrations.

    Each provider implements phone number lookup and connection testing.
    """

    @abstractmethod
    async def lookup_by_phone(self, phone: str) -> CRMContact | None:
        """Look up a contact by phone number.

        Args:
            phone: E.164 or national-format phone number.

        Returns:
            CRMContact if found, None if no match.
        """

    @abstractmethod
    async def test_connection(self) -> dict:
        """Test connectivity to the CRM API.

        Returns:
            Dict with 'success' (bool) and 'message' (str).
        """

    async def close(self) -> None:  # noqa: B027
        """Clean up resources (e.g. HTTP clients). Override if needed."""

"""Abstract base class for telephony provider integrations."""

import abc
from dataclasses import dataclass


@dataclass
class DIDSearchResult:
    """A single available DID returned from a provider search."""

    number: str
    monthly_cost: float
    setup_cost: float
    provider: str
    capabilities: dict


@dataclass
class DIDPurchaseResult:
    """Result of purchasing a DID from a provider."""

    number: str
    provider_sid: str
    provider: str


@dataclass
class TrunkProvisionRequest:
    """Request payload to create a SIP trunk at a provider."""

    name: str
    provider: str
    region: str
    channels: int
    config: dict


@dataclass
class TrunkProvisionResult:
    """Result of provisioning a SIP trunk at a provider."""

    provider_trunk_id: str
    host: str
    port: int
    username: str
    password: str


@dataclass
class TrunkTestResult:
    """Result of a SIP OPTIONS health-check against a provider trunk."""

    status: str
    latency_ms: float | None
    error: str | None


class TelephonyProvider(abc.ABC):
    """Abstract interface that every telephony provider must implement."""

    @abc.abstractmethod
    async def search_dids(
        self,
        area_code: str | None,
        state: str | None,
        quantity: int,
    ) -> list[DIDSearchResult]:
        """Search the provider's inventory for available DIDs."""

    @abc.abstractmethod
    async def purchase_did(self, number: str) -> DIDPurchaseResult:
        """Purchase (provision) a single DID number."""

    @abc.abstractmethod
    async def release_did(self, provider_sid: str) -> bool:
        """Release a previously purchased DID back to the provider."""

    @abc.abstractmethod
    async def configure_did(self, provider_sid: str, config: dict) -> bool:
        """Apply routing / feature configuration to a DID at the provider."""

    @abc.abstractmethod
    async def create_trunk(self, config: TrunkProvisionRequest) -> TrunkProvisionResult:
        """Create a new SIP trunk at the provider."""

    @abc.abstractmethod
    async def delete_trunk(self, provider_trunk_id: str) -> bool:
        """Delete (deprovision) a SIP trunk at the provider."""

    @abc.abstractmethod
    async def get_trunk_status(self, provider_trunk_id: str) -> str:
        """Return the current status string for a provider trunk."""

    @abc.abstractmethod
    async def test_trunk(self, provider_trunk_id: str) -> TrunkTestResult:
        """Run a SIP OPTIONS health-check against the trunk."""

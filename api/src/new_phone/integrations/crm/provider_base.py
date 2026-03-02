"""Base class and data types for CRM provider integrations."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TypeVar

import httpx
import structlog

logger = structlog.get_logger()

T = TypeVar("T")

# Default timeout: 10s connect, 30s read
CRM_HTTP_TIMEOUT = httpx.Timeout(10.0, read=30.0)

# Retry defaults
CRM_RETRY_ATTEMPTS = 3
CRM_RETRY_BACKOFF_SECONDS = (1.0, 2.0, 4.0)


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


async def crm_retry(
    coro_factory,
    *,
    attempts: int = CRM_RETRY_ATTEMPTS,
    backoff: tuple[float, ...] = CRM_RETRY_BACKOFF_SECONDS,
    provider_name: str = "crm",
):
    """Retry an async HTTP call with exponential backoff.

    Args:
        coro_factory: A zero-arg callable that returns a fresh awaitable each call.
        attempts: Maximum number of attempts.
        backoff: Sequence of sleep durations between attempts.
        provider_name: Used in log messages.

    Returns:
        The result of the awaitable on success.

    Raises:
        The last exception if all attempts are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return await coro_factory()
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt < attempts - 1:
                delay = backoff[min(attempt, len(backoff) - 1)]
                logger.warning(
                    f"{provider_name}_retry",
                    attempt=attempt + 1,
                    delay=delay,
                    error=str(exc),
                )
                await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]


def create_crm_client(**kwargs) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient with standard CRM timeouts.

    Extra kwargs are forwarded to AsyncClient (e.g. base_url, headers).
    """
    kwargs.setdefault("timeout", CRM_HTTP_TIMEOUT)
    return httpx.AsyncClient(**kwargs)


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

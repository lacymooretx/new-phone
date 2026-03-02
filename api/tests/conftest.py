import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient

# Fixed UUIDs for test data (match dev-seed.sql)
MSP_TENANT_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
ACME_TENANT_ID = uuid.UUID("b0000000-0000-0000-0000-000000000002")

# Test against the running API server
API_BASE_URL = "http://localhost:8000"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(base_url=API_BASE_URL) as ac:
        yield ac


@pytest.fixture
async def msp_admin_token(client: AsyncClient) -> str:
    """Get a JWT for the seeded MSP admin."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@msp.local", "password": "admin123"},
    )
    if response.status_code != 200:
        pytest.skip("Seed data not loaded — run `make seed` first")
    return response.json()["access_token"]


@pytest.fixture
async def acme_admin_token(client: AsyncClient) -> str:
    """Get a JWT for the seeded Acme tenant admin."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.local", "password": "admin123"},
    )
    if response.status_code != 200:
        pytest.skip("Seed data not loaded — run `make seed` first")
    return response.json()["access_token"]


@pytest.fixture
async def acme_manager_token(client: AsyncClient) -> str:
    """Get a JWT for the seeded Acme tenant manager (sales@acme.local)."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "sales@acme.local", "password": "admin123"},
    )
    if response.status_code != 200:
        pytest.skip("Seed data not loaded — run `make seed` first")
    return response.json()["access_token"]


@pytest.fixture
async def acme_user_token(client: AsyncClient) -> str:
    """Get a JWT for the seeded Acme tenant user (user@acme.local)."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@acme.local", "password": "admin123"},
    )
    if response.status_code != 200:
        pytest.skip("Seed data not loaded — run `make seed` first")
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

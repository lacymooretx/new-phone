import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header


@pytest.mark.asyncio
async def test_list_tenants_as_msp_admin(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        "/api/v1/tenants",
        headers=auth_header(msp_admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # msp + acme


@pytest.mark.asyncio
async def test_list_tenants_as_tenant_admin_denied(client: AsyncClient, acme_admin_token: str):
    """Tenant admins should not be able to list all tenants."""
    response = await client.get(
        "/api/v1/tenants",
        headers=auth_header(acme_admin_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_own_tenant(client: AsyncClient, acme_admin_token: str):
    response = await client.get(
        f"/api/v1/tenants/{ACME_TENANT_ID}",
        headers=auth_header(acme_admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "acme"


@pytest.mark.asyncio
async def test_get_other_tenant_denied(client: AsyncClient, acme_admin_token: str):
    """Tenant admin should not access MSP tenant."""
    response = await client.get(
        f"/api/v1/tenants/{MSP_TENANT_ID}",
        headers=auth_header(acme_admin_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_tenant(client: AsyncClient, msp_admin_token: str):
    slug = f"test-{uuid.uuid4().hex[:8]}"
    response = await client.post(
        "/api/v1/tenants",
        headers=auth_header(msp_admin_token),
        json={"name": "Test Tenant", "slug": slug},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == slug
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_tenant_duplicate_slug(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        "/api/v1/tenants",
        headers=auth_header(msp_admin_token),
        json={"name": "Acme Duplicate", "slug": "acme"},
    )
    assert response.status_code == 409

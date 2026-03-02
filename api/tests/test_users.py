import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header


@pytest.mark.asyncio
async def test_list_users_in_tenant(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"/api/v1/tenants/{ACME_TENANT_ID}/users",
        headers=auth_header(msp_admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_user_in_tenant(client: AsyncClient, msp_admin_token: str):
    unique = uuid.uuid4().hex[:8]
    response = await client.post(
        f"/api/v1/tenants/{ACME_TENANT_ID}/users",
        headers=auth_header(msp_admin_token),
        json={
            "email": f"testuser-{unique}@acme.local",
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
            "role": "tenant_user",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == f"testuser-{unique}@acme.local"
    assert str(data["tenant_id"]) == str(ACME_TENANT_ID)


@pytest.mark.asyncio
async def test_tenant_admin_cannot_access_other_tenant_users(
    client: AsyncClient, acme_admin_token: str
):
    """Acme admin should not see MSP tenant users."""
    response = await client.get(
        f"/api/v1/tenants/{MSP_TENANT_ID}/users",
        headers=auth_header(acme_admin_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_duplicate_email(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        f"/api/v1/tenants/{ACME_TENANT_ID}/users",
        headers=auth_header(msp_admin_token),
        json={
            "email": "admin@acme.local",
            "password": "password123",
            "first_name": "Duplicate",
            "last_name": "User",
        },
    )
    assert response.status_code == 409

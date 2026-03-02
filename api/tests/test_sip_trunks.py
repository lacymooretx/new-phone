import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/trunks"


@pytest.mark.asyncio
async def test_list_trunks(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1  # seeded


@pytest.mark.asyncio
async def test_create_trunk(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Test Trunk {uuid.uuid4().hex[:6]}",
            "auth_type": "registration",
            "host": "sip.test.com",
            "port": 5061,
            "username": "testuser",
            "password": "secretpass",
            "max_channels": 10,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["auth_type"] == "registration"
    assert data["username"] == "testuser"
    # Encrypted password must NEVER appear in response
    assert "encrypted_password" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_get_trunk(client: AsyncClient, msp_admin_token: str):
    trunks = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    trunk_id = trunks[0]["id"]

    response = await client.get(f"{BASE}/{trunk_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["id"] == trunk_id
    assert "encrypted_password" not in response.json()


@pytest.mark.asyncio
async def test_update_trunk(client: AsyncClient, msp_admin_token: str):
    trunks = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    trunk_id = trunks[0]["id"]

    response = await client.patch(
        f"{BASE}/{trunk_id}",
        headers=auth_header(msp_admin_token),
        json={"max_channels": 60},
    )
    assert response.status_code == 200
    assert response.json()["max_channels"] == 60


@pytest.mark.asyncio
async def test_deactivate_trunk(client: AsyncClient, msp_admin_token: str):
    resp = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Del Trunk {uuid.uuid4().hex[:6]}",
            "auth_type": "ip_auth",
            "host": "10.0.0.1",
            "ip_acl": "10.0.0.0/24",
        },
    )
    trunk_id = resp.json()["id"]

    response = await client.delete(f"{BASE}/{trunk_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_tenant_manager_cannot_manage_trunks(client: AsyncClient, acme_manager_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={
            "name": "Unauthorized Trunk",
            "auth_type": "registration",
            "host": "sip.evil.com",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_trunks(client: AsyncClient, acme_manager_token: str):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    # Manager has VIEW_TRUNKS but not MANAGE_TRUNKS
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_trunks(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/trunks"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403

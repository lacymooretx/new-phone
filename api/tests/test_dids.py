import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/dids"


@pytest.mark.asyncio
async def test_list_dids(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # seeded


@pytest.mark.asyncio
async def test_create_did(client: AsyncClient, msp_admin_token: str):
    unique = uuid.uuid4().int % 9000000 + 1000000
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "number": f"+1555{unique}",
            "provider": "manual",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["provider"] == "manual"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_did(client: AsyncClient, msp_admin_token: str):
    dids = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    did_id = dids[0]["id"]

    response = await client.get(f"{BASE}/{did_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["id"] == did_id


@pytest.mark.asyncio
async def test_update_did(client: AsyncClient, msp_admin_token: str):
    dids = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    did_id = dids[0]["id"]

    response = await client.patch(
        f"{BASE}/{did_id}",
        headers=auth_header(msp_admin_token),
        json={"status": "reserved"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "reserved"


@pytest.mark.asyncio
async def test_deactivate_did(client: AsyncClient, msp_admin_token: str):
    unique = uuid.uuid4().int % 9000000 + 1000000
    resp = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={"number": f"+1444{unique}", "provider": "manual"},
    )
    did_id = resp.json()["id"]

    response = await client.delete(f"{BASE}/{did_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_duplicate_did_number(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={"number": "+15551001000", "provider": "manual"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_invalid_e164_format(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={"number": "5551234567", "provider": "manual"},
    )
    assert response.status_code == 422  # validation error


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_dids(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_dids(client: AsyncClient, acme_manager_token: str):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/dids"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403

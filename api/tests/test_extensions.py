import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/extensions"


@pytest.mark.asyncio
async def test_list_extensions(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # seeded


@pytest.mark.asyncio
async def test_create_extension(client: AsyncClient, msp_admin_token: str):
    unique = uuid.uuid4().hex[:4]
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "extension_number": f"5{unique[:3]}",
            "dnd_enabled": True,
            "class_of_service": "local",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["dnd_enabled"] is True
    assert data["class_of_service"] == "local"
    assert "sip_username" in data
    # SIP password hash must NOT be in response
    assert "sip_password_hash" not in data


@pytest.mark.asyncio
async def test_get_extension(client: AsyncClient, msp_admin_token: str):
    exts = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    ext_id = exts[0]["id"]

    response = await client.get(f"{BASE}/{ext_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["id"] == ext_id


@pytest.mark.asyncio
async def test_update_extension(client: AsyncClient, msp_admin_token: str):
    exts = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    ext_id = exts[0]["id"]

    response = await client.patch(
        f"{BASE}/{ext_id}",
        headers=auth_header(msp_admin_token),
        json={"call_waiting": False, "max_registrations": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["call_waiting"] is False
    assert data["max_registrations"] == 5


@pytest.mark.asyncio
async def test_deactivate_extension(client: AsyncClient, msp_admin_token: str):
    resp = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={"extension_number": f"7{uuid.uuid4().hex[:3]}"},
    )
    ext_id = resp.json()["id"]

    response = await client.delete(f"{BASE}/{ext_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_reset_sip_password(client: AsyncClient, msp_admin_token: str):
    exts = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    ext_id = exts[0]["id"]

    response = await client.post(
        f"{BASE}/{ext_id}/reset-sip-password", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert "sip_password" in data
    assert len(data["sip_password"]) == 32


@pytest.mark.asyncio
async def test_duplicate_extension_number(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={"extension_number": "100"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_tenant_user_can_view_extensions(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_user_cannot_manage_extensions(client: AsyncClient, acme_user_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_user_token),
        json={"extension_number": "999"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_manage_extensions(client: AsyncClient, acme_manager_token: str):
    unique = uuid.uuid4().hex[:4]
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={"extension_number": f"6{unique[:3]}"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/extensions"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403

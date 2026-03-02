import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/voicemail-boxes"


@pytest.mark.asyncio
async def test_list_voicemail_boxes(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # seeded


@pytest.mark.asyncio
async def test_create_voicemail_box(client: AsyncClient, msp_admin_token: str):
    unique = uuid.uuid4().hex[:6]
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "mailbox_number": f"9{unique[:3]}",
            "pin": "5678",
            "greeting_type": "busy",
            "max_messages": 50,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["greeting_type"] == "busy"
    assert data["max_messages"] == 50
    assert "pin_hash" not in data


@pytest.mark.asyncio
async def test_get_voicemail_box(client: AsyncClient, msp_admin_token: str):
    # List first, then get one
    boxes = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    box_id = boxes[0]["id"]

    response = await client.get(f"{BASE}/{box_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["id"] == box_id


@pytest.mark.asyncio
async def test_update_voicemail_box(client: AsyncClient, msp_admin_token: str):
    boxes = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    box_id = boxes[0]["id"]

    response = await client.patch(
        f"{BASE}/{box_id}",
        headers=auth_header(msp_admin_token),
        json={"max_messages": 200},
    )
    assert response.status_code == 200
    assert response.json()["max_messages"] == 200


@pytest.mark.asyncio
async def test_deactivate_voicemail_box(client: AsyncClient, msp_admin_token: str):
    # Create one to deactivate
    resp = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={"mailbox_number": f"8{uuid.uuid4().hex[:3]}", "pin": "1234"},
    )
    box_id = resp.json()["id"]

    response = await client.delete(f"{BASE}/{box_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_reset_pin(client: AsyncClient, msp_admin_token: str):
    boxes = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    box_id = boxes[0]["id"]

    response = await client.post(
        f"{BASE}/{box_id}/reset-pin", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert "pin" in data
    assert len(data["pin"]) == 4


@pytest.mark.asyncio
async def test_duplicate_mailbox_number(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={"mailbox_number": "100", "pin": "1234"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_tenant_user_can_view_voicemail(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_user_cannot_manage_voicemail(client: AsyncClient, acme_user_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_user_token),
        json={"mailbox_number": "999", "pin": "1234"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other_tenant = f"/api/v1/tenants/{MSP_TENANT_ID}/voicemail-boxes"
    response = await client.get(other_tenant, headers=auth_header(acme_admin_token))
    assert response.status_code == 403

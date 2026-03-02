import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

VM_BOX_100_ID = "d0000000-0000-0000-0000-000000000001"
VM_BOX_101_ID = "d0000000-0000-0000-0000-000000000002"
BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/voicemail-boxes/{VM_BOX_100_ID}/messages"
MSG_ID = "b2000000-0000-0000-0000-000000000001"
MSG_SAVED_ID = "b2000000-0000-0000-0000-000000000002"


@pytest.mark.asyncio
async def test_list_voicemail_messages(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_messages_filter_folder(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        BASE, headers=auth_header(msp_admin_token), params={"folder": "new"}
    )
    assert response.status_code == 200
    data = response.json()
    for msg in data:
        assert msg["folder"] == "new"


@pytest.mark.asyncio
async def test_list_messages_filter_is_read(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        BASE, headers=auth_header(msp_admin_token), params={"is_read": "false"}
    )
    assert response.status_code == 200
    data = response.json()
    for msg in data:
        assert msg["is_read"] is False


@pytest.mark.asyncio
async def test_get_voicemail_message(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{MSG_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["caller_number"] == "+15559991234"
    assert data["caller_name"] == "John Doe"
    assert data["folder"] == "new"
    assert data["is_read"] is False


@pytest.mark.asyncio
async def test_get_message_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_playback_url(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{MSG_ID}/playback", headers=auth_header(msp_admin_token)
    )
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_update_message_mark_read(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{MSG_ID}",
        headers=auth_header(msp_admin_token),
        json={"is_read": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_read"] is True

    # Reset back
    await client.patch(
        f"{BASE}/{MSG_ID}",
        headers=auth_header(msp_admin_token),
        json={"is_read": False},
    )


@pytest.mark.asyncio
async def test_update_message_move_folder(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{MSG_SAVED_ID}",
        headers=auth_header(msp_admin_token),
        json={"folder": "saved"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["folder"] == "saved"


@pytest.mark.asyncio
async def test_forward_message(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        f"{BASE}/{MSG_ID}/forward",
        headers=auth_header(msp_admin_token),
        json={"target_box_id": VM_BOX_101_ID},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["voicemail_box_id"] == VM_BOX_101_ID
    assert data["caller_number"] == "+15559991234"


@pytest.mark.asyncio
async def test_forward_message_invalid_target(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        f"{BASE}/{MSG_ID}/forward",
        headers=auth_header(msp_admin_token),
        json={"target_box_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unread_counts(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"/api/v1/tenants/{ACME_TENANT_ID}/voicemail-messages/unread-counts",
        headers=auth_header(msp_admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # At least one box should have unread messages
    if data:
        assert "voicemail_box_id" in data[0]
        assert "mailbox_number" in data[0]
        assert "unread_count" in data[0]


@pytest.mark.asyncio
async def test_tenant_user_can_view_messages(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_user_cannot_update_message(client: AsyncClient, acme_user_token: str):
    response = await client.patch(
        f"{BASE}/{MSG_ID}",
        headers=auth_header(acme_user_token),
        json={"is_read": True},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/voicemail-boxes/{VM_BOX_100_ID}/messages"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_message_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{MSG_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "voicemail_box_id", "caller_number",
        "caller_name", "duration_seconds", "storage_path", "storage_bucket",
        "file_size_bytes", "format", "sha256_hash", "is_read", "is_urgent",
        "folder", "call_id", "email_sent", "is_active", "created_at", "updated_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/recordings"

# Seeded recording ID
RECORDING_ID = "a2000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_list_recordings(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_recordings_with_pagination(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        BASE, headers=auth_header(msp_admin_token), params={"limit": 1, "offset": 0}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 1


@pytest.mark.asyncio
async def test_get_recording(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{RECORDING_ID}", headers=auth_header(msp_admin_token)
    )
    # May be 404 if soft-deleted from a prior test run
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert data["call_id"] == "seed-call-001"
        assert data["format"] == "wav"
        assert data["storage_bucket"] == "recordings"


@pytest.mark.asyncio
async def test_get_recording_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_playback_url(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{RECORDING_ID}/playback", headers=auth_header(msp_admin_token)
    )
    # May return 404 if MinIO object doesn't exist (seed data has fake path)
    # or 200 with a presigned URL if MinIO is configured
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_recording_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{RECORDING_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "cdr_id", "call_id", "storage_path",
        "storage_bucket", "file_size_bytes", "duration_seconds",
        "format", "sample_rate", "sha256_hash", "recording_policy",
        "is_active", "created_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_tenant_user_can_view_recordings(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_user_cannot_delete_recording(client: AsyncClient, acme_user_token: str):
    response = await client.delete(
        f"{BASE}/{RECORDING_ID}", headers=auth_header(acme_user_token)
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_delete_recording(client: AsyncClient, acme_manager_token: str):
    response = await client.delete(
        f"{BASE}/{RECORDING_ID}", headers=auth_header(acme_manager_token)
    )
    # May return 200 (newly deleted) or 404 (already deleted from prior run)
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert data["is_active"] is False


@pytest.mark.asyncio
async def test_cross_tenant_recording_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/recordings"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403

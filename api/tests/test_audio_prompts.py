import io
import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/audio-prompts"
PROMPT_ID = "b1000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_list_audio_prompts(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_prompts_filter_category(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        BASE, headers=auth_header(msp_admin_token), params={"category": "ivr_greeting"}
    )
    assert response.status_code == 200
    data = response.json()
    for prompt in data:
        assert prompt["category"] == "ivr_greeting"


@pytest.mark.asyncio
async def test_get_audio_prompt(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{PROMPT_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Main Greeting"
    assert data["category"] == "ivr_greeting"


@pytest.mark.asyncio
async def test_get_prompt_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_audio_prompt(client: AsyncClient, msp_admin_token: str):
    # Create a minimal WAV file (just header, no real audio)
    wav_data = b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt " + (16).to_bytes(4, "little")
    wav_data += (1).to_bytes(2, "little")  # PCM
    wav_data += (1).to_bytes(2, "little")  # mono
    wav_data += (8000).to_bytes(4, "little")  # sample rate
    wav_data += (16000).to_bytes(4, "little")  # byte rate
    wav_data += (2).to_bytes(2, "little")  # block align
    wav_data += (16).to_bytes(2, "little")  # bits per sample
    wav_data += b"data" + (0).to_bytes(4, "little")

    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        files={"file": ("test-prompt.wav", io.BytesIO(wav_data), "audio/wav")},
        data={"name": f"Test Prompt {uuid.uuid4().hex[:8]}", "category": "general"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"].startswith("Test Prompt")
    assert data["format"] == "wav"
    assert data["file_size_bytes"] > 0
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_upload_duplicate_name_fails(client: AsyncClient, msp_admin_token: str):
    wav_data = b"RIFF" + b"\x00" * 40
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        files={"file": ("test.wav", io.BytesIO(wav_data), "audio/wav")},
        data={"name": "Main Greeting", "category": "general"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_playback_url(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{PROMPT_ID}/playback", headers=auth_header(msp_admin_token)
    )
    # 404 expected since seed data has no actual MinIO file
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_prompts(client: AsyncClient, acme_user_token: str):
    """Tenant user doesn't have VIEW_IVR permission."""
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_prompts(client: AsyncClient, acme_manager_token: str):
    """Tenant manager has VIEW_IVR permission."""
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_manager_cannot_upload_prompt(client: AsyncClient, acme_manager_token: str):
    """Tenant manager doesn't have MANAGE_IVR permission."""
    wav_data = b"RIFF" + b"\x00" * 40
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        files={"file": ("test.wav", io.BytesIO(wav_data), "audio/wav")},
        data={"name": "Manager Test", "category": "general"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/audio-prompts"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_prompt_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{PROMPT_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "name", "description", "category",
        "storage_path", "storage_bucket", "file_size_bytes",
        "duration_seconds", "format", "sample_rate", "sha256_hash",
        "local_path", "is_active", "created_at", "updated_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

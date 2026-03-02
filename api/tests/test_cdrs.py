import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/cdrs"

# Seeded CDR IDs
CDR_ANSWERED_ID = "a1000000-0000-0000-0000-000000000001"
CDR_OUTBOUND_ID = "a1000000-0000-0000-0000-000000000002"
CDR_NOANSWER_ID = "a1000000-0000-0000-0000-000000000003"


@pytest.mark.asyncio
async def test_list_cdrs(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # seeded CDRs


@pytest.mark.asyncio
async def test_list_cdrs_with_pagination(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        BASE, headers=auth_header(msp_admin_token), params={"limit": 1, "offset": 0}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_list_cdrs_filter_direction(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        BASE, headers=auth_header(msp_admin_token), params={"direction": "inbound"}
    )
    assert response.status_code == 200
    data = response.json()
    for cdr in data:
        assert cdr["direction"] == "inbound"


@pytest.mark.asyncio
async def test_list_cdrs_filter_disposition(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        BASE, headers=auth_header(msp_admin_token), params={"disposition": "answered"}
    )
    assert response.status_code == 200
    data = response.json()
    for cdr in data:
        assert cdr["disposition"] == "answered"


@pytest.mark.asyncio
async def test_get_cdr(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{CDR_ANSWERED_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["call_id"] == "seed-call-001"
    assert data["direction"] == "inbound"
    assert data["disposition"] == "answered"
    assert data["has_recording"] is True


@pytest.mark.asyncio
async def test_get_cdr_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_cdrs_csv(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/export", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.strip().split("\n")
    assert len(lines) >= 2  # header + at least 1 row
    header = lines[0]
    assert "call_id" in header
    assert "disposition" in header


@pytest.mark.asyncio
async def test_tenant_user_can_view_cdrs(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cross_tenant_cdr_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/cdrs"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cdr_cleanup_requires_msp_admin(client: AsyncClient, acme_admin_token: str):
    response = await client.post(
        "/api/v1/admin/cdr-cleanup",
        headers=auth_header(acme_admin_token),
        json={"days": 365},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cdr_cleanup_msp_admin(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        "/api/v1/admin/cdr-cleanup",
        headers=auth_header(msp_admin_token),
        json={"days": 3650},
    )
    assert response.status_code == 200
    data = response.json()
    assert "deleted" in data


@pytest.mark.asyncio
async def test_cdr_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{CDR_ANSWERED_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "call_id", "direction", "caller_number",
        "caller_name", "called_number", "disposition", "duration_seconds",
        "billable_seconds", "ring_seconds", "start_time", "end_time",
        "has_recording", "created_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

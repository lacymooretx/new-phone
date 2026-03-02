import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/time-conditions"
TC_ID = "b3000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_list_time_conditions(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_time_condition(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{TC_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Business Hours"
    assert data["timezone"] == "America/New_York"
    assert isinstance(data["rules"], list)
    assert len(data["rules"]) == 2
    assert data["match_destination_type"] == "extension"
    assert data["nomatch_destination_type"] == "voicemail"


@pytest.mark.asyncio
async def test_get_time_condition_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_time_condition(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Weekend Hours {uuid.uuid4().hex[:8]}",
            "description": "Weekend routing",
            "timezone": "America/Chicago",
            "rules": [
                {"type": "day_of_week", "days": [6, 7], "label": "Weekend"}
            ],
            "match_destination_type": "voicemail",
            "match_destination_id": "d0000000-0000-0000-0000-000000000001",
            "nomatch_destination_type": "extension",
            "nomatch_destination_id": "e0000000-0000-0000-0000-000000000001",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["timezone"] == "America/Chicago"
    assert len(data["rules"]) == 1
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_create_duplicate_name_fails(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": "Business Hours",
            "rules": [],
            "match_destination_type": "extension",
            "nomatch_destination_type": "voicemail",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_time_condition(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{TC_ID}",
        headers=auth_header(msp_admin_token),
        json={"description": "Updated description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_time_conditions(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_time_conditions(client: AsyncClient, acme_manager_token: str):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_manager_cannot_create_time_condition(client: AsyncClient, acme_manager_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={
            "name": "Manager TC",
            "rules": [],
            "match_destination_type": "extension",
            "nomatch_destination_type": "voicemail",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/time-conditions"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tc_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{TC_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "name", "description", "timezone", "rules",
        "match_destination_type", "match_destination_id",
        "nomatch_destination_type", "nomatch_destination_id",
        "enabled", "is_active", "created_at", "updated_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

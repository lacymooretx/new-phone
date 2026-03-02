import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/holiday-calendars"
CALENDAR_ID = "d2000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_list_holiday_calendars(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_holiday_calendar(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{CALENDAR_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "US Federal Holidays 2026"
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) == 5


@pytest.mark.asyncio
async def test_get_holiday_calendar_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_holiday_calendar_with_entries(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Test Holidays {uuid.uuid4().hex[:8]}",
            "description": "Test calendar",
            "entries": [
                {
                    "name": "Test Day",
                    "date": "2026-06-15",
                    "recur_annually": False,
                    "all_day": True,
                },
                {
                    "name": "Half Day",
                    "date": "2026-06-16",
                    "recur_annually": False,
                    "all_day": False,
                    "start_time": "12:00:00",
                    "end_time": "17:00:00",
                },
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["entries"]) == 2
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_duplicate_name_fails(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": "US Federal Holidays 2026",
            "entries": [],
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_holiday_calendar_replace_entries(client: AsyncClient, msp_admin_token: str):
    # Create a calendar first
    create_resp = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Update Test {uuid.uuid4().hex[:8]}",
            "entries": [
                {"name": "Original", "date": "2026-03-01", "all_day": True},
            ],
        },
    )
    assert create_resp.status_code == 201
    cal_id = create_resp.json()["id"]

    # Update with new entries (replace-all)
    response = await client.patch(
        f"{BASE}/{cal_id}",
        headers=auth_header(msp_admin_token),
        json={
            "description": "Updated",
            "entries": [
                {"name": "Replaced Entry 1", "date": "2026-04-01", "all_day": True},
                {"name": "Replaced Entry 2", "date": "2026-04-02", "all_day": True},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated"
    assert len(data["entries"]) == 2
    entry_names = [e["name"] for e in data["entries"]]
    assert "Replaced Entry 1" in entry_names
    assert "Replaced Entry 2" in entry_names


@pytest.mark.asyncio
async def test_deactivate_holiday_calendar(client: AsyncClient, msp_admin_token: str):
    create_resp = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Delete Me {uuid.uuid4().hex[:8]}",
            "entries": [],
        },
    )
    assert create_resp.status_code == 201
    cal_id = create_resp.json()["id"]

    response = await client.delete(
        f"{BASE}/{cal_id}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_calendars(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_calendars(client: AsyncClient, acme_manager_token: str):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_manager_cannot_create_calendar(client: AsyncClient, acme_manager_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={
            "name": "Manager Calendar",
            "entries": [],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/holiday-calendars"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_calendar_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{CALENDAR_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "name", "description", "is_active",
        "entries", "created_at", "updated_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

    # Check entry fields
    entry = data["entries"][0]
    entry_fields = ["id", "calendar_id", "name", "date", "recur_annually", "all_day"]
    for field in entry_fields:
        assert field in entry, f"Missing entry field: {field}"


@pytest.mark.asyncio
async def test_holiday_entry_partial_day(client: AsyncClient, msp_admin_token: str):
    """Christmas Eve Afternoon should have start/end times."""
    response = await client.get(
        f"{BASE}/{CALENDAR_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    entries = response.json()["entries"]
    partial = [e for e in entries if e["name"] == "Christmas Eve Afternoon"]
    assert len(partial) == 1
    assert partial[0]["all_day"] is False
    assert partial[0]["start_time"] is not None
    assert partial[0]["end_time"] is not None


@pytest.mark.asyncio
async def test_tc_has_holiday_calendar_field(client: AsyncClient, msp_admin_token: str):
    """Time condition Business Hours should now have holiday_calendar_id set."""
    tc_url = f"/api/v1/tenants/{ACME_TENANT_ID}/time-conditions/b3000000-0000-0000-0000-000000000001"
    response = await client.get(tc_url, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert data["holiday_calendar_id"] == CALENDAR_ID
    assert data["manual_override"] is None

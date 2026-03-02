import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/conference-bridges"
BRIDGE_ID = "c8000000-0000-0000-0000-000000000001"
SECURE_BRIDGE_ID = "c8000000-0000-0000-0000-000000000002"


# ── List ──


@pytest.mark.asyncio
async def test_list_conference_bridges(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_list_conference_bridges_has_seeded_data(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    names = [b["name"] for b in data]
    assert "Main Conference" in names
    assert "Secure Conference" in names


# ── Get ──


@pytest.mark.asyncio
async def test_get_conference_bridge(client: AsyncClient, msp_admin_token: str):
    response = await client.get(f"{BASE}/{BRIDGE_ID}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Main Conference"
    assert data["room_number"] == "800"
    assert data["max_participants"] == 50


@pytest.mark.asyncio
async def test_get_secure_conference(client: AsyncClient, msp_admin_token: str):
    response = await client.get(f"{BASE}/{SECURE_BRIDGE_ID}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert data["participant_pin"] == "1234"
    assert data["moderator_pin"] == "5678"
    assert data["wait_for_moderator"] is True


@pytest.mark.asyncio
async def test_get_conference_bridge_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 404


# ── Create ──


@pytest.mark.asyncio
async def test_create_conference_bridge_minimal(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Test Bridge {uuid.uuid4().hex[:8]}",
            "room_number": f"8{uuid.uuid4().hex[:2]}",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["max_participants"] == 50
    assert data["wait_for_moderator"] is False
    assert data["muted_on_join"] is False
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_create_conference_bridge_with_pins(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"PIN Bridge {uuid.uuid4().hex[:8]}",
            "room_number": f"8{uuid.uuid4().hex[:2]}",
            "participant_pin": "9999",
            "moderator_pin": "7777",
            "wait_for_moderator": True,
            "muted_on_join": True,
            "record_conference": True,
            "max_participants": 100,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["participant_pin"] == "9999"
    assert data["moderator_pin"] == "7777"
    assert data["wait_for_moderator"] is True
    assert data["muted_on_join"] is True
    assert data["record_conference"] is True
    assert data["max_participants"] == 100


@pytest.mark.asyncio
async def test_create_conference_bridge_duplicate_name_fails(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": "Main Conference",
            "room_number": "899",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_conference_bridge_duplicate_room_fails(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Unique Name {uuid.uuid4().hex[:8]}",
            "room_number": "800",
        },
    )
    assert response.status_code == 409


# ── Update ──


@pytest.mark.asyncio
async def test_update_conference_bridge_description(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{BRIDGE_ID}",
        headers=auth_header(msp_admin_token),
        json={"description": "Updated conference room"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated conference room"


@pytest.mark.asyncio
async def test_update_conference_bridge_settings(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{BRIDGE_ID}",
        headers=auth_header(msp_admin_token),
        json={"max_participants": 200, "announce_join_leave": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["max_participants"] == 200
    assert data["announce_join_leave"] is False
    # Reset
    await client.patch(
        f"{BASE}/{BRIDGE_ID}",
        headers=auth_header(msp_admin_token),
        json={"max_participants": 50, "announce_join_leave": True},
    )


@pytest.mark.asyncio
async def test_update_conference_bridge_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.patch(
        f"{BASE}/{fake_id}",
        headers=auth_header(msp_admin_token),
        json={"description": "nope"},
    )
    assert response.status_code == 404


# ── Delete (deactivate) ──


@pytest.mark.asyncio
async def test_deactivate_conference_bridge(client: AsyncClient, msp_admin_token: str):
    create = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"ToDelete {uuid.uuid4().hex[:8]}",
            "room_number": f"8{uuid.uuid4().hex[:2]}",
        },
    )
    assert create.status_code == 201
    bid = create.json()["id"]

    response = await client.delete(f"{BASE}/{bid}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    listing = await client.get(BASE, headers=auth_header(msp_admin_token))
    ids = [b["id"] for b in listing.json()]
    assert bid not in ids


@pytest.mark.asyncio
async def test_deactivate_conference_bridge_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.delete(f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 404


# ── RBAC ──


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_conferences(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_conferences(client: AsyncClient, acme_manager_token: str):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_manager_cannot_create_conference(client: AsyncClient, acme_manager_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={
            "name": "Manager Bridge",
            "room_number": "899",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_admin_can_manage_conferences(client: AsyncClient, acme_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_admin_token),
        json={
            "name": f"Admin Bridge {uuid.uuid4().hex[:8]}",
            "room_number": f"8{uuid.uuid4().hex[:2]}",
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/conference-bridges"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


# ── Response Fields ──


@pytest.mark.asyncio
async def test_conference_bridge_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(f"{BASE}/{BRIDGE_ID}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "name", "room_number", "description",
        "max_participants", "participant_pin", "moderator_pin",
        "wait_for_moderator", "announce_join_leave", "moh_prompt_id",
        "record_conference", "muted_on_join", "enabled",
        "is_active", "created_at", "updated_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

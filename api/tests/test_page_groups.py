import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/page-groups"
PAGE_GROUP_ID = "c9000000-0000-0000-0000-000000000001"
EXT_100_ID = "e0000000-0000-0000-0000-000000000001"
EXT_101_ID = "e0000000-0000-0000-0000-000000000002"
EXT_102_ID = "e0000000-0000-0000-0000-000000000003"


# ── List ──


@pytest.mark.asyncio
async def test_list_page_groups(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_page_groups_returns_members(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    group = next((g for g in data if g["id"] == PAGE_GROUP_ID), None)
    assert group is not None
    assert len(group["members"]) >= 3


# ── Get ──


@pytest.mark.asyncio
async def test_get_page_group(client: AsyncClient, msp_admin_token: str):
    response = await client.get(f"{BASE}/{PAGE_GROUP_ID}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "All Phones"
    assert data["page_number"] == "500"
    assert data["page_mode"] == "one_way"
    assert isinstance(data["members"], list)
    assert len(data["members"]) >= 3


@pytest.mark.asyncio
async def test_get_page_group_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 404


# ── Create ──


@pytest.mark.asyncio
async def test_create_page_group_minimal(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Test Page {uuid.uuid4().hex[:8]}",
            "page_number": f"5{uuid.uuid4().hex[:2]}",
            "members": [],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["page_mode"] == "one_way"
    assert data["timeout"] == 60
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_page_group_with_members(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Office Page {uuid.uuid4().hex[:8]}",
            "page_number": f"5{uuid.uuid4().hex[:2]}",
            "page_mode": "two_way",
            "timeout": 120,
            "members": [
                {"extension_id": EXT_100_ID, "position": 0},
                {"extension_id": EXT_101_ID, "position": 1},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["page_mode"] == "two_way"
    assert data["timeout"] == 120
    assert len(data["members"]) == 2


@pytest.mark.asyncio
async def test_create_page_group_duplicate_name_fails(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": "All Phones",
            "page_number": "599",
            "members": [],
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_page_group_duplicate_number_fails(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"New Page {uuid.uuid4().hex[:8]}",
            "page_number": "500",
            "members": [],
        },
    )
    assert response.status_code == 409


# ── Update ──


@pytest.mark.asyncio
async def test_update_page_group_description(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{PAGE_GROUP_ID}",
        headers=auth_header(msp_admin_token),
        json={"description": "Updated all phones page"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated all phones page"


@pytest.mark.asyncio
async def test_update_page_group_mode(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{PAGE_GROUP_ID}",
        headers=auth_header(msp_admin_token),
        json={"page_mode": "two_way"},
    )
    assert response.status_code == 200
    assert response.json()["page_mode"] == "two_way"
    # Reset
    await client.patch(
        f"{BASE}/{PAGE_GROUP_ID}",
        headers=auth_header(msp_admin_token),
        json={"page_mode": "one_way"},
    )


@pytest.mark.asyncio
async def test_update_page_group_replace_members(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{PAGE_GROUP_ID}",
        headers=auth_header(msp_admin_token),
        json={
            "members": [
                {"extension_id": EXT_100_ID, "position": 0},
                {"extension_id": EXT_101_ID, "position": 1},
                {"extension_id": EXT_102_ID, "position": 2},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["members"]) == 3


@pytest.mark.asyncio
async def test_update_page_group_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.patch(
        f"{BASE}/{fake_id}",
        headers=auth_header(msp_admin_token),
        json={"description": "nope"},
    )
    assert response.status_code == 404


# ── Delete (deactivate) ──


@pytest.mark.asyncio
async def test_deactivate_page_group(client: AsyncClient, msp_admin_token: str):
    create = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"ToDelete {uuid.uuid4().hex[:8]}",
            "page_number": f"5{uuid.uuid4().hex[:2]}",
            "members": [],
        },
    )
    assert create.status_code == 201
    gid = create.json()["id"]

    response = await client.delete(f"{BASE}/{gid}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    listing = await client.get(BASE, headers=auth_header(msp_admin_token))
    ids = [g["id"] for g in listing.json()]
    assert gid not in ids


@pytest.mark.asyncio
async def test_deactivate_page_group_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.delete(f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 404


# ── RBAC ──


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_page_groups(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_page_groups(client: AsyncClient, acme_manager_token: str):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_manager_cannot_create_page_group(client: AsyncClient, acme_manager_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={
            "name": "Manager Page",
            "page_number": "599",
            "members": [],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_admin_can_manage_page_groups(client: AsyncClient, acme_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_admin_token),
        json={
            "name": f"Admin Page {uuid.uuid4().hex[:8]}",
            "page_number": f"5{uuid.uuid4().hex[:2]}",
            "members": [],
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/page-groups"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


# ── Response Fields ──


@pytest.mark.asyncio
async def test_page_group_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(f"{BASE}/{PAGE_GROUP_ID}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "name", "page_number", "description",
        "page_mode", "timeout", "is_active", "created_at", "updated_at", "members",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_page_group_member_response_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(f"{BASE}/{PAGE_GROUP_ID}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    members = response.json()["members"]
    assert len(members) >= 1
    member = members[0]
    assert "id" in member
    assert "page_group_id" in member
    assert "extension_id" in member
    assert "position" in member


# ── Extension pickup_group ──


@pytest.mark.asyncio
async def test_extension_response_includes_pickup_group(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"/api/v1/tenants/{ACME_TENANT_ID}/extensions/{EXT_100_ID}",
        headers=auth_header(msp_admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "pickup_group" in data
    assert data["pickup_group"] == "1"

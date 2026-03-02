import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/ring-groups"


@pytest.mark.asyncio
async def test_list_ring_groups(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1  # seeded


@pytest.mark.asyncio
async def test_create_ring_group_with_members(client: AsyncClient, msp_admin_token: str):
    # Get extensions to add as members
    exts = (
        await client.get(
            f"/api/v1/tenants/{ACME_TENANT_ID}/extensions",
            headers=auth_header(msp_admin_token),
        )
    ).json()
    ext_ids = [e["id"] for e in exts[:2]]

    unique = uuid.uuid4().hex[:4]
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "group_number": f"*7{unique[:2]}",
            "name": f"Test Group {unique}",
            "ring_strategy": "sequential",
            "ring_time": 30,
            "member_extension_ids": ext_ids,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["ring_strategy"] == "sequential"
    assert data["ring_time"] == 30
    assert len(data["member_extension_ids"]) == 2
    # Order preserved
    assert data["member_extension_ids"][0] == ext_ids[0]
    assert data["member_extension_ids"][1] == ext_ids[1]


@pytest.mark.asyncio
async def test_get_ring_group(client: AsyncClient, msp_admin_token: str):
    groups = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    group_id = groups[0]["id"]

    response = await client.get(f"{BASE}/{group_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["id"] == group_id
    assert "member_extension_ids" in response.json()


@pytest.mark.asyncio
async def test_update_ring_group_reorder_members(client: AsyncClient, msp_admin_token: str):
    groups = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    group_id = groups[0]["id"]
    current_members = groups[0]["member_extension_ids"]

    if len(current_members) >= 2:
        # Reverse the order
        reversed_members = list(reversed(current_members))
        response = await client.patch(
            f"{BASE}/{group_id}",
            headers=auth_header(msp_admin_token),
            json={"member_extension_ids": reversed_members},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["member_extension_ids"] == reversed_members


@pytest.mark.asyncio
async def test_update_ring_group_settings(client: AsyncClient, msp_admin_token: str):
    groups = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    group_id = groups[0]["id"]

    response = await client.patch(
        f"{BASE}/{group_id}",
        headers=auth_header(msp_admin_token),
        json={"ring_strategy": "round_robin", "confirm_calls": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ring_strategy"] == "round_robin"
    assert data["confirm_calls"] is True


@pytest.mark.asyncio
async def test_deactivate_ring_group(client: AsyncClient, msp_admin_token: str):
    unique = uuid.uuid4().hex[:4]
    resp = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "group_number": f"*8{unique[:2]}",
            "name": f"Del Group {unique}",
        },
    )
    group_id = resp.json()["id"]

    response = await client.delete(f"{BASE}/{group_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_duplicate_group_number(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={"group_number": "*601", "name": "Duplicate"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_tenant_manager_can_manage_ring_groups(
    client: AsyncClient, acme_manager_token: str
):
    unique = uuid.uuid4().hex[:4]
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={
            "group_number": f"*9{unique[:2]}",
            "name": f"Mgr Group {unique}",
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_tenant_user_can_view_ring_groups(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_user_cannot_manage_ring_groups(client: AsyncClient, acme_user_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_user_token),
        json={"group_number": "*999", "name": "Unauthorized"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/ring-groups"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403

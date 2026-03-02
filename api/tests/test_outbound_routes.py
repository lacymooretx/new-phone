import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/outbound-routes"


@pytest.mark.asyncio
async def test_list_outbound_routes(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1  # seeded


@pytest.mark.asyncio
async def test_create_outbound_route_with_trunks(client: AsyncClient, msp_admin_token: str):
    # Get a trunk to assign
    trunks = (
        await client.get(
            f"/api/v1/tenants/{ACME_TENANT_ID}/trunks",
            headers=auth_header(msp_admin_token),
        )
    ).json()
    trunk_id = trunks[0]["id"]

    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Route {uuid.uuid4().hex[:6]}",
            "dial_pattern": "NXXNXXXXXX",
            "strip_digits": 0,
            "priority": 200,
            "trunk_ids": [trunk_id],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["dial_pattern"] == "NXXNXXXXXX"
    assert len(data["trunk_ids"]) == 1
    assert data["trunk_ids"][0] == trunk_id


@pytest.mark.asyncio
async def test_get_outbound_route(client: AsyncClient, msp_admin_token: str):
    routes = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    route_id = routes[0]["id"]

    response = await client.get(f"{BASE}/{route_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["id"] == route_id
    assert "trunk_ids" in response.json()


@pytest.mark.asyncio
async def test_update_outbound_route_reorder_trunks(client: AsyncClient, msp_admin_token: str):
    routes = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    route_id = routes[0]["id"]

    # Create a second trunk
    resp = await client.post(
        f"/api/v1/tenants/{ACME_TENANT_ID}/trunks",
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Second Trunk {uuid.uuid4().hex[:6]}",
            "auth_type": "ip_auth",
            "host": "10.1.1.1",
            "ip_acl": "10.1.1.0/24",
        },
    )
    trunk2_id = resp.json()["id"]

    trunks = (
        await client.get(
            f"/api/v1/tenants/{ACME_TENANT_ID}/trunks",
            headers=auth_header(msp_admin_token),
        )
    ).json()
    trunk1_id = trunks[0]["id"]

    # Update with ordered trunk list
    response = await client.patch(
        f"{BASE}/{route_id}",
        headers=auth_header(msp_admin_token),
        json={"trunk_ids": [trunk2_id, trunk1_id]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trunk_ids"][0] == trunk2_id
    assert data["trunk_ids"][1] == trunk1_id


@pytest.mark.asyncio
async def test_deactivate_outbound_route(client: AsyncClient, msp_admin_token: str):
    resp = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Del Route {uuid.uuid4().hex[:6]}",
            "dial_pattern": "011.",
            "priority": 999,
        },
    )
    route_id = resp.json()["id"]

    response = await client.delete(f"{BASE}/{route_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_tenant_manager_cannot_manage_outbound_routes(
    client: AsyncClient, acme_manager_token: str
):
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={"name": "Unauthorized", "dial_pattern": "NXXXXXX"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_outbound_routes(
    client: AsyncClient, acme_manager_token: str
):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_outbound_routes(
    client: AsyncClient, acme_user_token: str
):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/outbound-routes"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403

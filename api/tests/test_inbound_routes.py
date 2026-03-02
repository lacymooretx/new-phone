import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/inbound-routes"


@pytest.mark.asyncio
async def test_list_inbound_routes(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1  # seeded


@pytest.mark.asyncio
async def test_create_inbound_route(client: AsyncClient, msp_admin_token: str):
    # Get an extension to route to
    exts = (
        await client.get(
            f"/api/v1/tenants/{ACME_TENANT_ID}/extensions",
            headers=auth_header(msp_admin_token),
        )
    ).json()
    ext_id = exts[0]["id"]

    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Test Route {uuid.uuid4().hex[:6]}",
            "destination_type": "extension",
            "destination_id": ext_id,
            "cid_name_prefix": "[TEST]",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["destination_type"] == "extension"
    assert data["cid_name_prefix"] == "[TEST]"


@pytest.mark.asyncio
async def test_get_inbound_route(client: AsyncClient, msp_admin_token: str):
    routes = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    route_id = routes[0]["id"]

    response = await client.get(f"{BASE}/{route_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["id"] == route_id


@pytest.mark.asyncio
async def test_update_inbound_route(client: AsyncClient, msp_admin_token: str):
    routes = (await client.get(BASE, headers=auth_header(msp_admin_token))).json()
    route_id = routes[0]["id"]

    response = await client.patch(
        f"{BASE}/{route_id}",
        headers=auth_header(msp_admin_token),
        json={"enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_deactivate_inbound_route(client: AsyncClient, msp_admin_token: str):
    resp = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Del Route {uuid.uuid4().hex[:6]}",
            "destination_type": "terminate",
        },
    )
    route_id = resp.json()["id"]

    response = await client.delete(f"{BASE}/{route_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_tenant_manager_cannot_manage_inbound_routes(
    client: AsyncClient, acme_manager_token: str
):
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={"name": "Unauthorized", "destination_type": "terminate"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_inbound_routes(
    client: AsyncClient, acme_manager_token: str
):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_inbound_routes(
    client: AsyncClient, acme_user_token: str
):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/inbound-routes"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403

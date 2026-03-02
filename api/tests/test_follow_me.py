import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

EXT_100_ID = "e0000000-0000-0000-0000-000000000001"
EXT_101_ID = "e0000000-0000-0000-0000-000000000002"


def _fm_url(ext_id: str) -> str:
    return f"/api/v1/tenants/{ACME_TENANT_ID}/extensions/{ext_id}/follow-me"


@pytest.mark.asyncio
async def test_get_follow_me_existing(client: AsyncClient, msp_admin_token: str):
    """Get follow-me for seeded ext 100 — should have config."""
    response = await client.get(
        _fm_url(EXT_100_ID), headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["strategy"] == "sequential"
    assert data["ring_extension_first"] is True
    assert len(data["destinations"]) == 2


@pytest.mark.asyncio
async def test_get_follow_me_empty_default(client: AsyncClient, msp_admin_token: str):
    """Get follow-me for ext without config — should return empty default."""
    response = await client.get(
        _fm_url(EXT_101_ID), headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["destinations"] == []


@pytest.mark.asyncio
async def test_upsert_follow_me_create(client: AsyncClient, msp_admin_token: str):
    """PUT follow-me for ext without config — should create."""
    response = await client.put(
        _fm_url(EXT_101_ID),
        headers=auth_header(msp_admin_token),
        json={
            "enabled": True,
            "strategy": "ring_all_external",
            "ring_extension_first": False,
            "extension_ring_time": 15,
            "destinations": [
                {"destination": "+15551112222", "ring_time": 20},
                {"destination": "+15553334444", "ring_time": 15},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["strategy"] == "ring_all_external"
    assert data["ring_extension_first"] is False
    assert data["extension_ring_time"] == 15
    assert len(data["destinations"]) == 2
    assert data["destinations"][0]["destination"] == "+15551112222"


@pytest.mark.asyncio
async def test_upsert_follow_me_update(client: AsyncClient, msp_admin_token: str):
    """PUT follow-me for ext with existing config — should update."""
    response = await client.put(
        _fm_url(EXT_100_ID),
        headers=auth_header(msp_admin_token),
        json={
            "enabled": False,
            "strategy": "sequential",
            "ring_extension_first": True,
            "extension_ring_time": 30,
            "destinations": [
                {"destination": "+15559999999", "ring_time": 25},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["extension_ring_time"] == 30
    assert len(data["destinations"]) == 1
    assert data["destinations"][0]["destination"] == "+15559999999"


@pytest.mark.asyncio
async def test_follow_me_uses_extension_permissions(client: AsyncClient, acme_user_token: str):
    """Tenant user can VIEW extensions → can GET follow-me."""
    response = await client.get(
        _fm_url(EXT_100_ID), headers=auth_header(acme_user_token)
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_follow_me_manage_requires_permission(client: AsyncClient, acme_user_token: str):
    """Tenant user cannot MANAGE extensions → cannot PUT follow-me."""
    response = await client.put(
        _fm_url(EXT_100_ID),
        headers=auth_header(acme_user_token),
        json={
            "enabled": True,
            "strategy": "sequential",
            "destinations": [],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_follow_me_denied(client: AsyncClient, acme_admin_token: str):
    """Acme admin cannot access follow-me for MSP tenant's extensions."""
    url = f"/api/v1/tenants/{MSP_TENANT_ID}/extensions/{EXT_100_ID}/follow-me"
    response = await client.get(url, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_follow_me_empty_destinations(client: AsyncClient, msp_admin_token: str):
    """PUT follow-me with empty destinations — should clear destinations."""
    # First ensure ext 101 has follow-me
    await client.put(
        _fm_url(EXT_101_ID),
        headers=auth_header(msp_admin_token),
        json={
            "enabled": True,
            "strategy": "sequential",
            "destinations": [{"destination": "+15551112222", "ring_time": 20}],
        },
    )

    # Now clear destinations
    response = await client.put(
        _fm_url(EXT_101_ID),
        headers=auth_header(msp_admin_token),
        json={
            "enabled": True,
            "strategy": "sequential",
            "destinations": [],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["destinations"] == []


@pytest.mark.asyncio
async def test_tenant_manager_can_manage_follow_me(client: AsyncClient, acme_manager_token: str):
    """Tenant manager has MANAGE_EXTENSIONS → can PUT follow-me."""
    response = await client.put(
        _fm_url(EXT_100_ID),
        headers=auth_header(acme_manager_token),
        json={
            "enabled": True,
            "strategy": "sequential",
            "ring_extension_first": True,
            "extension_ring_time": 25,
            "destinations": [{"destination": "+15559991234", "ring_time": 20}],
        },
    )
    assert response.status_code == 200

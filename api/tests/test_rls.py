"""Test that Row-Level Security properly isolates tenant data."""

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header


@pytest.mark.asyncio
async def test_rls_tenant_isolation(client: AsyncClient, acme_admin_token: str):
    """Acme admin should only see Acme users, not MSP users."""
    response = await client.get(
        f"/api/v1/tenants/{ACME_TENANT_ID}/users",
        headers=auth_header(acme_admin_token),
    )
    assert response.status_code == 200
    users = response.json()

    # All returned users should belong to Acme tenant
    for user in users:
        assert str(user["tenant_id"]) == str(ACME_TENANT_ID)


@pytest.mark.asyncio
async def test_rls_cross_tenant_user_access_denied(
    client: AsyncClient, acme_admin_token: str, msp_admin_token: str
):
    """Create a user in MSP tenant, verify Acme admin can't see them via user endpoint."""
    # Get MSP users as MSP admin
    msp_response = await client.get(
        f"/api/v1/tenants/{MSP_TENANT_ID}/users",
        headers=auth_header(msp_admin_token),
    )
    assert msp_response.status_code == 200
    msp_users = msp_response.json()

    if not msp_users:
        pytest.skip("No MSP users found")

    msp_user_id = msp_users[0]["id"]

    # Acme admin tries to access MSP user directly
    response = await client.get(
        f"/api/v1/tenants/{MSP_TENANT_ID}/users/{msp_user_id}",
        headers=auth_header(acme_admin_token),
    )
    assert response.status_code == 403

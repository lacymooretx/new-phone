import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, auth_header

BASE = "/api/v1/audit-logs"


@pytest.mark.asyncio
async def test_msp_admin_can_list_audit_logs(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_tenant_admin_can_list_audit_logs(client: AsyncClient, acme_admin_token: str):
    response = await client.get(BASE, headers=auth_header(acme_admin_token))
    assert response.status_code == 200
    data = response.json()
    # Tenant admin should only see their tenant's logs
    for item in data["items"]:
        assert item["tenant_id"] == str(ACME_TENANT_ID)


@pytest.mark.asyncio
async def test_tenant_user_cannot_list_audit_logs(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_cannot_list_audit_logs(client: AsyncClient, acme_manager_token: str):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    # Per plan: TENANT_MANAGER should NOT have VIEW_AUDIT_LOGS
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_filter_by_action(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        BASE,
        headers=auth_header(msp_admin_token),
        params={"action": "login"},
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["action"] == "login"


@pytest.mark.asyncio
async def test_audit_log_filter_by_tenant(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        BASE,
        headers=auth_header(msp_admin_token),
        params={"tenant_id": str(ACME_TENANT_ID)},
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["tenant_id"] == str(ACME_TENANT_ID)


@pytest.mark.asyncio
async def test_audit_log_pagination(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        BASE,
        headers=auth_header(msp_admin_token),
        params={"page": 1, "per_page": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["per_page"] == 5
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_login_produces_audit_log(client: AsyncClient, msp_admin_token: str):
    """Login should produce an audit entry."""
    # The msp_admin_token fixture already logged in.
    # Now check for audit logs with action=login
    response = await client.get(
        BASE,
        headers=auth_header(msp_admin_token),
        params={"action": "login", "resource_type": "auth"},
    )
    assert response.status_code == 200
    data = response.json()
    # Should have at least the fixture login + seed entry
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_extension_create_produces_audit_log(client: AsyncClient, msp_admin_token: str):
    """Creating an extension should produce an audit entry."""
    unique = uuid.uuid4().hex[:4]
    ext_base = f"/api/v1/tenants/{ACME_TENANT_ID}/extensions"
    resp = await client.post(
        ext_base,
        headers=auth_header(msp_admin_token),
        json={"extension_number": f"8{unique[:3]}"},
    )
    assert resp.status_code == 201

    # Check audit log
    response = await client.get(
        BASE,
        headers=auth_header(msp_admin_token),
        params={"action": "create", "resource_type": "extension"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(item["action"] == "create" and item["resource_type"] == "extension" for item in data["items"])


@pytest.mark.asyncio
async def test_failed_login_produces_audit_log(client: AsyncClient, msp_admin_token: str):
    """Failed login should produce an audit entry."""
    # Attempt bad login
    await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.local", "password": "wrongpassword"},
    )

    # Check audit log
    response = await client.get(
        BASE,
        headers=auth_header(msp_admin_token),
        params={"action": "login_failed", "resource_type": "auth"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

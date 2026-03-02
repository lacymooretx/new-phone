import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/caller-id-rules"
RULE_ID = "d1000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_list_caller_id_rules(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_get_caller_id_rule(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{RULE_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Block Anonymous"
    assert data["rule_type"] == "block"
    assert data["match_pattern"] == "anonymous"
    assert data["action"] == "reject"
    assert data["priority"] == 100


@pytest.mark.asyncio
async def test_get_caller_id_rule_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_caller_id_rule(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Test Block {uuid.uuid4().hex[:8]}",
            "rule_type": "block",
            "match_pattern": "+1800*",
            "action": "reject",
            "priority": 10,
            "notes": "Block toll-free",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rule_type"] == "block"
    assert data["match_pattern"] == "+1800*"
    assert data["action"] == "reject"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_duplicate_name_fails(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": "Block Anonymous",
            "rule_type": "block",
            "match_pattern": "anonymous",
            "action": "reject",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_caller_id_rule(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{RULE_ID}",
        headers=auth_header(msp_admin_token),
        json={"notes": "Updated notes"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == "Updated notes"


@pytest.mark.asyncio
async def test_deactivate_caller_id_rule(client: AsyncClient, msp_admin_token: str):
    # Create a rule to deactivate
    create_resp = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Delete Me {uuid.uuid4().hex[:8]}",
            "rule_type": "block",
            "match_pattern": "+1999*",
            "action": "hangup",
        },
    )
    assert create_resp.status_code == 201
    rule_id = create_resp.json()["id"]

    response = await client.delete(
        f"{BASE}/{rule_id}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_cid_rules(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_cid_rules(client: AsyncClient, acme_manager_token: str):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_manager_cannot_create_cid_rule(client: AsyncClient, acme_manager_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={
            "name": "Manager Rule",
            "rule_type": "block",
            "match_pattern": "+1*",
            "action": "reject",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/caller-id-rules"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cid_rule_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{RULE_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "name", "rule_type", "match_pattern", "action",
        "destination_id", "priority", "notes", "is_active", "created_at", "updated_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/queues"
QUEUE_ID = "b6000000-0000-0000-0000-000000000001"
EXT_100_ID = "e0000000-0000-0000-0000-000000000001"
EXT_101_ID = "e0000000-0000-0000-0000-000000000002"
EXT_102_ID = "e0000000-0000-0000-0000-000000000003"


# ── List ──


@pytest.mark.asyncio
async def test_list_queues(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_queues_returns_members(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    queue = next((q for q in data if q["id"] == QUEUE_ID), None)
    assert queue is not None
    assert len(queue["members"]) >= 3


# ── Get ──


@pytest.mark.asyncio
async def test_get_queue(client: AsyncClient, msp_admin_token: str):
    response = await client.get(f"{BASE}/{QUEUE_ID}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Sales Queue"
    assert data["queue_number"] == "600"
    assert data["strategy"] == "longest-idle-agent"
    assert isinstance(data["members"], list)
    assert len(data["members"]) >= 3


@pytest.mark.asyncio
async def test_get_queue_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 404


# ── Create ──


@pytest.mark.asyncio
async def test_create_queue_minimal(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Support Queue {uuid.uuid4().hex[:8]}",
            "queue_number": f"7{uuid.uuid4().hex[:2]}",
            "members": [],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["strategy"] == "longest-idle-agent"
    assert data["max_wait_time"] == 300
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_create_queue_with_members(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Tech Queue {uuid.uuid4().hex[:8]}",
            "queue_number": f"8{uuid.uuid4().hex[:2]}",
            "strategy": "ring-all",
            "ring_timeout": 20,
            "wrapup_time": 15,
            "members": [
                {"extension_id": EXT_100_ID, "level": 1, "position": 1},
                {"extension_id": EXT_101_ID, "level": 1, "position": 2},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["strategy"] == "ring-all"
    assert data["ring_timeout"] == 20
    assert data["wrapup_time"] == 15
    assert len(data["members"]) == 2


@pytest.mark.asyncio
async def test_create_queue_all_strategies(client: AsyncClient, msp_admin_token: str):
    strategies = [
        "ring-all", "longest-idle-agent", "round-robin", "top-down",
        "agent-with-least-talk-time", "agent-with-fewest-calls",
        "sequentially-by-agent-order", "random", "ring-progressively",
    ]
    for strategy in strategies:
        response = await client.post(
            BASE,
            headers=auth_header(msp_admin_token),
            json={
                "name": f"Strat {strategy} {uuid.uuid4().hex[:4]}",
                "queue_number": f"9{uuid.uuid4().hex[:2]}",
                "strategy": strategy,
                "members": [],
            },
        )
        assert response.status_code == 201, f"Failed for strategy: {strategy}"
        assert response.json()["strategy"] == strategy


@pytest.mark.asyncio
async def test_create_queue_duplicate_name_fails(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": "Sales Queue",
            "queue_number": "699",
            "members": [],
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_queue_duplicate_number_fails(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"New Queue {uuid.uuid4().hex[:8]}",
            "queue_number": "600",
            "members": [],
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_queue_with_overflow(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Overflow Queue {uuid.uuid4().hex[:8]}",
            "queue_number": f"6{uuid.uuid4().hex[:2]}",
            "max_wait_time": 60,
            "overflow_destination_type": "voicemail",
            "overflow_destination_id": str(uuid.uuid4()),
            "caller_exit_key": "*",
            "members": [],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["max_wait_time"] == 60
    assert data["overflow_destination_type"] == "voicemail"
    assert data["caller_exit_key"] == "*"


# ── Update ──


@pytest.mark.asyncio
async def test_update_queue_description(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{QUEUE_ID}",
        headers=auth_header(msp_admin_token),
        json={"description": "Updated sales queue"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated sales queue"


@pytest.mark.asyncio
async def test_update_queue_strategy(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{QUEUE_ID}",
        headers=auth_header(msp_admin_token),
        json={"strategy": "round-robin"},
    )
    assert response.status_code == 200
    assert response.json()["strategy"] == "round-robin"
    # Reset
    await client.patch(
        f"{BASE}/{QUEUE_ID}",
        headers=auth_header(msp_admin_token),
        json={"strategy": "longest-idle-agent"},
    )


@pytest.mark.asyncio
async def test_update_queue_replace_members(client: AsyncClient, msp_admin_token: str):
    """Members are replaced wholesale on update."""
    response = await client.patch(
        f"{BASE}/{QUEUE_ID}",
        headers=auth_header(msp_admin_token),
        json={
            "members": [
                {"extension_id": EXT_100_ID, "level": 1, "position": 1},
                {"extension_id": EXT_101_ID, "level": 1, "position": 2},
                {"extension_id": EXT_102_ID, "level": 2, "position": 1},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["members"]) == 3


@pytest.mark.asyncio
async def test_update_queue_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.patch(
        f"{BASE}/{fake_id}",
        headers=auth_header(msp_admin_token),
        json={"description": "nope"},
    )
    assert response.status_code == 404


# ── Delete (deactivate) ──


@pytest.mark.asyncio
async def test_deactivate_queue(client: AsyncClient, msp_admin_token: str):
    # Create a temp queue first
    create = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"ToDelete {uuid.uuid4().hex[:8]}",
            "queue_number": f"5{uuid.uuid4().hex[:2]}",
            "members": [],
        },
    )
    assert create.status_code == 201
    qid = create.json()["id"]

    # Deactivate it
    response = await client.delete(f"{BASE}/{qid}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Confirm it's gone from listing
    listing = await client.get(BASE, headers=auth_header(msp_admin_token))
    ids = [q["id"] for q in listing.json()]
    assert qid not in ids


@pytest.mark.asyncio
async def test_deactivate_queue_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.delete(f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token))
    assert response.status_code == 404


# ── Agent Status ──


@pytest.mark.asyncio
async def test_set_agent_status_available(client: AsyncClient, msp_admin_token: str):
    response = await client.put(
        f"{BASE}/{QUEUE_ID}/agents/{EXT_100_ID}/status",
        headers=auth_header(msp_admin_token),
        json={"status": "Available"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["agent_status"] == "Available"
    assert data["extension_id"] == EXT_100_ID


@pytest.mark.asyncio
async def test_set_agent_status_logged_out(client: AsyncClient, msp_admin_token: str):
    response = await client.put(
        f"{BASE}/{QUEUE_ID}/agents/{EXT_100_ID}/status",
        headers=auth_header(msp_admin_token),
        json={"status": "Logged Out"},
    )
    assert response.status_code == 200
    assert response.json()["agent_status"] == "Logged Out"
    # Reset
    await client.put(
        f"{BASE}/{QUEUE_ID}/agents/{EXT_100_ID}/status",
        headers=auth_header(msp_admin_token),
        json={"status": "Available"},
    )


@pytest.mark.asyncio
async def test_set_agent_status_on_break(client: AsyncClient, msp_admin_token: str):
    response = await client.put(
        f"{BASE}/{QUEUE_ID}/agents/{EXT_100_ID}/status",
        headers=auth_header(msp_admin_token),
        json={"status": "On Break"},
    )
    assert response.status_code == 200
    assert response.json()["agent_status"] == "On Break"
    # Reset
    await client.put(
        f"{BASE}/{QUEUE_ID}/agents/{EXT_100_ID}/status",
        headers=auth_header(msp_admin_token),
        json={"status": "Available"},
    )


@pytest.mark.asyncio
async def test_set_agent_status_non_member_fails(client: AsyncClient, msp_admin_token: str):
    fake_ext = str(uuid.uuid4())
    response = await client.put(
        f"{BASE}/{QUEUE_ID}/agents/{fake_ext}/status",
        headers=auth_header(msp_admin_token),
        json={"status": "Available"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_agent_statuses(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/agent-status",
        headers=auth_header(msp_admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should include agents with agent_status set
    assert len(data) >= 1
    for agent in data:
        assert "extension_id" in agent
        assert "extension_number" in agent
        assert "agent_status" in agent


# ── Queue Stats ──


@pytest.mark.asyncio
async def test_get_queue_stats(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{QUEUE_ID}/stats",
        headers=auth_header(msp_admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["queue_id"] == QUEUE_ID
    assert data["queue_name"] == "Sales Queue"
    assert "waiting_count" in data
    assert "agents_logged_in" in data
    assert "agents_available" in data
    assert "agents_on_call" in data
    assert "longest_wait_seconds" in data


@pytest.mark.asyncio
async def test_get_queue_stats_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"{BASE}/{fake_id}/stats",
        headers=auth_header(msp_admin_token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_all_queue_stats(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/stats",
        headers=auth_header(msp_admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


# ── RBAC ──


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_queues(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_queues(client: AsyncClient, acme_manager_token: str):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_manager_cannot_create_queue(client: AsyncClient, acme_manager_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={
            "name": "Manager Queue",
            "queue_number": "699",
            "members": [],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_admin_can_manage_queues(client: AsyncClient, acme_admin_token: str):
    # Tenant admin should be able to create
    response = await client.post(
        BASE,
        headers=auth_header(acme_admin_token),
        json={
            "name": f"Admin Queue {uuid.uuid4().hex[:8]}",
            "queue_number": f"4{uuid.uuid4().hex[:2]}",
            "members": [],
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/queues"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


# ── Response Fields ──


@pytest.mark.asyncio
async def test_queue_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(f"{BASE}/{QUEUE_ID}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "name", "queue_number", "description",
        "strategy", "moh_prompt_id", "max_wait_time",
        "max_wait_time_with_no_agent", "tier_rules_apply",
        "tier_rule_wait_second", "tier_rule_wait_multiply_level",
        "tier_rule_no_agent_no_wait", "discard_abandoned_after",
        "abandoned_resume_allowed", "caller_exit_key",
        "wrapup_time", "ring_timeout", "announce_frequency",
        "announce_prompt_id", "overflow_destination_type",
        "overflow_destination_id", "record_calls",
        "enabled", "is_active", "created_at", "updated_at", "members",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_queue_member_response_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(f"{BASE}/{QUEUE_ID}", headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    members = response.json()["members"]
    assert len(members) >= 1
    member = members[0]
    assert "id" in member
    assert "queue_id" in member
    assert "extension_id" in member
    assert "level" in member
    assert "position" in member


# ── Extension agent_status visible in extension response ──


@pytest.mark.asyncio
async def test_extension_response_includes_agent_status(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"/api/v1/tenants/{ACME_TENANT_ID}/extensions/{EXT_100_ID}",
        headers=auth_header(msp_admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "agent_status" in data

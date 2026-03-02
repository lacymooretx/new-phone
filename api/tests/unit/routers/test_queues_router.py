"""Tests for new_phone.routers.queues — queue CRUD + permissions."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from new_phone.deps.auth import get_admin_db, get_current_user
from new_phone.models.user import UserRole
from new_phone.routers import queues
from tests.unit.conftest import TENANT_ACME_ID, TENANT_GLOBEX_ID, make_user


@pytest.fixture
def app(mock_db, acme_admin_user):
    test_app = FastAPI()
    test_app.include_router(queues.router, prefix="/api/v1")

    async def override_db():
        yield mock_db

    test_app.dependency_overrides[get_admin_db] = override_db
    test_app.dependency_overrides[get_current_user] = lambda: acme_admin_user
    yield test_app
    test_app.dependency_overrides.clear()


def _mock_queue(**overrides):
    q = MagicMock()
    q.id = overrides.get("id", uuid.uuid4())
    q.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    q.name = overrides.get("name", "Support")
    q.queue_number = overrides.get("queue_number", "5000")
    q.description = overrides.get("description")
    q.strategy = overrides.get("strategy", "longest-idle-agent")
    q.is_active = overrides.get("is_active", True)
    q.members = overrides.get("members", [])
    q.moh_prompt_id = None
    q.max_wait_time = 300
    q.max_wait_time_with_no_agent = 120
    q.tier_rules_apply = True
    q.tier_rule_wait_second = 300
    q.tier_rule_wait_multiply_level = True
    q.tier_rule_no_agent_no_wait = False
    q.discard_abandoned_after = 60
    q.abandoned_resume_allowed = False
    q.caller_exit_key = None
    q.wrapup_time = 0
    q.ring_timeout = 30
    q.announce_frequency = 0
    q.announce_prompt_id = None
    q.overflow_destination_type = None
    q.overflow_destination_id = None
    q.record_calls = False
    q.enabled = True
    q.disposition_required = False
    q.disposition_code_list_id = None
    from datetime import UTC, datetime

    q.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    q.updated_at = datetime(2024, 1, 1, tzinfo=UTC)
    return q


class TestListQueues:
    async def test_happy_path(self, app, client):
        q1 = _mock_queue(name="Support")
        with patch("new_phone.routers.queues.QueueService") as MockSvc:
            MockSvc.return_value.list_queues = AsyncMock(return_value=[q1])
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/queues")
        assert resp.status_code == 200

    async def test_cross_tenant_403(self, app, client):
        resp = await client.get(f"/api/v1/tenants/{TENANT_GLOBEX_ID}/queues")
        assert resp.status_code == 403

    async def test_tenant_user_cannot_view(self, app, client):
        user = make_user(role=UserRole.TENANT_USER)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/queues")
        assert resp.status_code == 403


class TestCreateQueue:
    async def test_success_201(self, app, client):
        queue = _mock_queue(name="New Queue")
        with (
            patch("new_phone.routers.queues.QueueService") as MockSvc,
            patch("new_phone.routers.queues._sync_queue_change", new_callable=AsyncMock),
        ):
            MockSvc.return_value.create_queue = AsyncMock(return_value=queue)
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ACME_ID}/queues",
                json={
                    "name": "New Queue",
                    "queue_number": "5001",
                    "members": [],
                },
            )
        assert resp.status_code == 201

    async def test_duplicate_409(self, app, client):
        with patch("new_phone.routers.queues.QueueService") as MockSvc:
            MockSvc.return_value.create_queue = AsyncMock(side_effect=ValueError("already exists"))
            resp = await client.post(
                f"/api/v1/tenants/{TENANT_ACME_ID}/queues",
                json={
                    "name": "Support",
                    "queue_number": "5000",
                    "members": [],
                },
            )
        assert resp.status_code == 409

    async def test_tenant_user_cannot_create(self, app, client):
        user = make_user(role=UserRole.TENANT_USER)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.post(
            f"/api/v1/tenants/{TENANT_ACME_ID}/queues",
            json={"name": "X", "queue_number": "9999", "members": []},
        )
        assert resp.status_code == 403


class TestGetQueue:
    async def test_found(self, app, client):
        queue_id = uuid.uuid4()
        queue = _mock_queue(id=queue_id)
        with patch("new_phone.routers.queues.QueueService") as MockSvc:
            MockSvc.return_value.get_queue = AsyncMock(return_value=queue)
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/queues/{queue_id}")
        assert resp.status_code == 200

    async def test_not_found_404(self, app, client):
        with patch("new_phone.routers.queues.QueueService") as MockSvc:
            MockSvc.return_value.get_queue = AsyncMock(return_value=None)
            resp = await client.get(f"/api/v1/tenants/{TENANT_ACME_ID}/queues/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestUpdateQueue:
    async def test_success(self, app, client):
        queue_id = uuid.uuid4()
        queue = _mock_queue(id=queue_id)
        with (
            patch("new_phone.routers.queues.QueueService") as MockSvc,
            patch("new_phone.routers.queues._sync_queue_change", new_callable=AsyncMock),
        ):
            MockSvc.return_value.update_queue = AsyncMock(return_value=queue)
            resp = await client.patch(
                f"/api/v1/tenants/{TENANT_ACME_ID}/queues/{queue_id}",
                json={"description": "Updated"},
            )
        assert resp.status_code == 200


class TestDeactivateQueue:
    async def test_success(self, app, client):
        queue_id = uuid.uuid4()
        queue = _mock_queue(id=queue_id, is_active=False)
        with (
            patch("new_phone.routers.queues.QueueService") as MockSvc,
            patch("new_phone.routers.queues._sync_queue_change", new_callable=AsyncMock),
        ):
            MockSvc.return_value.deactivate = AsyncMock(return_value=queue)
            resp = await client.delete(f"/api/v1/tenants/{TENANT_ACME_ID}/queues/{queue_id}")
        assert resp.status_code == 200

    async def test_tenant_manager_cannot_delete(self, app, client):
        user = make_user(role=UserRole.TENANT_MANAGER)
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.delete(f"/api/v1/tenants/{TENANT_ACME_ID}/queues/{uuid.uuid4()}")
        assert resp.status_code == 403

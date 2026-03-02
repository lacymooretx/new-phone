"""Tests for new_phone.services.queue_service — queue CRUD, members, agent status."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.queue_service import QueueService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_queue(**overrides):
    q = MagicMock()
    q.id = overrides.get("id", uuid.uuid4())
    q.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    q.name = overrides.get("name", "Support")
    q.queue_number = overrides.get("queue_number", "5000")
    q.is_active = overrides.get("is_active", True)
    q.members = overrides.get("members", [])
    return q


def _make_member(extension_id=None, agent_status="Available"):
    m = MagicMock()
    m.extension_id = extension_id or uuid.uuid4()
    m.level = 1
    m.position = 0
    ext = MagicMock()
    ext.id = m.extension_id
    ext.is_active = True
    ext.agent_status = agent_status
    ext.extension_number = "100"
    m.extension = ext
    return m


def _make_extension(**overrides):
    ext = MagicMock()
    ext.id = overrides.get("id", uuid.uuid4())
    ext.tenant_id = overrides.get("tenant_id", TENANT_ACME_ID)
    ext.extension_number = overrides.get("extension_number", "100")
    ext.is_active = overrides.get("is_active", True)
    ext.agent_status = overrides.get("agent_status")
    return ext


class TestListQueues:
    async def test_returns_list(self, mock_db):
        q1 = _make_queue(name="Support")
        q2 = _make_queue(name="Sales")
        mock_db.execute.return_value = make_scalars_result([q1, q2])

        service = QueueService(mock_db)
        result = await service.list_queues(TENANT_ACME_ID)
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = QueueService(mock_db)
        result = await service.list_queues(TENANT_ACME_ID)
        assert result == []


class TestGetQueue:
    async def test_found(self, mock_db):
        queue = _make_queue(name="Support")
        mock_db.execute.return_value = make_scalar_result(queue)
        service = QueueService(mock_db)
        result = await service.get_queue(TENANT_ACME_ID, queue.id)
        assert result.name == "Support"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = QueueService(mock_db)
        result = await service.get_queue(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateQueue:
    async def test_success(self, mock_db):
        from new_phone.schemas.queue import QueueCreate, QueueMemberCreate

        # Duplicate name check → None, duplicate number check → None
        mock_db.execute.side_effect = [
            make_scalar_result(None),
            make_scalar_result(None),
        ]

        service = QueueService(mock_db)
        data = QueueCreate(
            name="New Queue",
            queue_number="5001",
            members=[QueueMemberCreate(extension_id=uuid.uuid4(), level=1, position=1)],
        )
        await service.create_queue(TENANT_ACME_ID, data)
        # Queue + 1 member = 2 add calls
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_awaited()

    async def test_duplicate_name_raises(self, mock_db):
        from new_phone.schemas.queue import QueueCreate

        existing = _make_queue(name="Support")
        mock_db.execute.return_value = make_scalar_result(existing)

        service = QueueService(mock_db)
        data = QueueCreate(name="Support", queue_number="5001", members=[])
        with pytest.raises(ValueError, match="already exists"):
            await service.create_queue(TENANT_ACME_ID, data)

    async def test_duplicate_number_raises(self, mock_db):
        from new_phone.schemas.queue import QueueCreate

        existing = _make_queue(queue_number="5000")
        mock_db.execute.side_effect = [
            make_scalar_result(None),  # name check passes
            make_scalar_result(existing),  # number check fails
        ]

        service = QueueService(mock_db)
        data = QueueCreate(name="Unique Name", queue_number="5000", members=[])
        with pytest.raises(ValueError, match="already exists"):
            await service.create_queue(TENANT_ACME_ID, data)


class TestUpdateQueue:
    async def test_success(self, mock_db):
        from new_phone.schemas.queue import QueueUpdate

        queue = _make_queue(name="Old")
        mock_db.execute.return_value = make_scalar_result(queue)

        service = QueueService(mock_db)
        data = QueueUpdate(description="Updated description")
        await service.update_queue(TENANT_ACME_ID, queue.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.queue import QueueUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = QueueService(mock_db)
        data = QueueUpdate(description="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_queue(TENANT_ACME_ID, uuid.uuid4(), data)

    async def test_duplicate_name_on_update_raises(self, mock_db):
        from new_phone.schemas.queue import QueueUpdate

        queue = _make_queue(name="Original")
        conflicting = _make_queue(name="Taken")
        mock_db.execute.side_effect = [
            make_scalar_result(queue),  # get_queue
            make_scalar_result(conflicting),  # name uniqueness check
        ]

        service = QueueService(mock_db)
        data = QueueUpdate(name="Taken")
        with pytest.raises(ValueError, match="already exists"):
            await service.update_queue(TENANT_ACME_ID, queue.id, data)


class TestDeactivate:
    async def test_success(self, mock_db):
        queue = _make_queue(is_active=True)
        mock_db.execute.return_value = make_scalar_result(queue)
        service = QueueService(mock_db)
        await service.deactivate(TENANT_ACME_ID, queue.id)
        assert queue.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = QueueService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.deactivate(TENANT_ACME_ID, uuid.uuid4())


class TestSetAgentStatus:
    async def test_success(self, mock_db):
        ext_id = uuid.uuid4()
        member = _make_member(extension_id=ext_id)
        queue = _make_queue(members=[member])
        ext = _make_extension(id=ext_id)

        mock_db.execute.side_effect = [
            make_scalar_result(queue),  # get_queue
            make_scalar_result(ext),  # get extension
        ]

        service = QueueService(mock_db)
        await service.set_agent_status(TENANT_ACME_ID, queue.id, ext_id, "On Break")
        assert ext.agent_status == "On Break"

    async def test_queue_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = QueueService(mock_db)
        with pytest.raises(ValueError, match="Queue not found"):
            await service.set_agent_status(TENANT_ACME_ID, uuid.uuid4(), uuid.uuid4(), "Available")

    async def test_extension_not_member_raises(self, mock_db):
        queue = _make_queue(members=[])  # no members
        mock_db.execute.return_value = make_scalar_result(queue)
        service = QueueService(mock_db)
        with pytest.raises(ValueError, match="not a member"):
            await service.set_agent_status(TENANT_ACME_ID, queue.id, uuid.uuid4(), "Available")


class TestGetAgentStatuses:
    async def test_returns_agents(self, mock_db):
        e1 = _make_extension(agent_status="Available")
        e2 = _make_extension(agent_status="On Break")
        mock_db.execute.return_value = make_scalars_result([e1, e2])

        service = QueueService(mock_db)
        result = await service.get_agent_statuses(TENANT_ACME_ID)
        assert len(result) == 2


class TestGetQueueStats:
    async def test_returns_stats(self, mock_db):
        member = _make_member(agent_status="Available")
        queue = _make_queue(members=[member])
        mock_db.execute.return_value = make_scalar_result(queue)

        service = QueueService(mock_db)
        stats = await service.get_queue_stats(TENANT_ACME_ID, queue.id)
        assert stats["agents_available"] == 1
        assert stats["agents_logged_in"] == 1

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = QueueService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.get_queue_stats(TENANT_ACME_ID, uuid.uuid4())

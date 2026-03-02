"""Tests for new_phone.services.queue_service — queue CRUD, members, agent status."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from new_phone.schemas.queue import QueueCreate, QueueMemberCreate, QueueUpdate
from new_phone.services.queue_service import QueueService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result, make_scalars_result


def _make_queue(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        name="Support Queue",
        queue_number="800",
        description="Support queue",
        strategy="longest-idle-agent",
        moh_prompt_id=None,
        max_wait_time=300,
        max_wait_time_with_no_agent=120,
        tier_rules_apply=True,
        tier_rule_wait_second=300,
        tier_rule_wait_multiply_level=True,
        tier_rule_no_agent_no_wait=False,
        discard_abandoned_after=60,
        abandoned_resume_allowed=False,
        caller_exit_key=None,
        wrapup_time=0,
        ring_timeout=30,
        announce_frequency=0,
        announce_prompt_id=None,
        overflow_destination_type=None,
        overflow_destination_id=None,
        record_calls=False,
        enabled=True,
        is_active=True,
        members=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestListQueues:
    async def test_returns_queues(self, mock_db):
        q1 = _make_queue(name="Q1")
        q2 = _make_queue(name="Q2")
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
        queue = _make_queue()
        mock_db.execute.return_value = make_scalar_result(queue)
        service = QueueService(mock_db)
        result = await service.get_queue(TENANT_ACME_ID, queue.id)
        assert result is queue

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = QueueService(mock_db)
        result = await service.get_queue(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


class TestCreateQueue:
    async def test_success_with_members(self, mock_db):
        # name check -> None, queue_number check -> None
        mock_db.execute.side_effect = [
            make_scalar_result(None),
            make_scalar_result(None),
        ]
        ext_id = uuid.uuid4()
        data = QueueCreate(
            name="New Queue",
            queue_number="801",
            members=[QueueMemberCreate(extension_id=ext_id, level=1, position=1)],
        )

        service = QueueService(mock_db)
        await service.create_queue(TENANT_ACME_ID, data)
        # 1 queue + 1 member = 2 adds
        assert mock_db.add.call_count == 2
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    async def test_duplicate_name_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(_make_queue())
        data = QueueCreate(name="Support Queue", queue_number="802")

        service = QueueService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_queue(TENANT_ACME_ID, data)

    async def test_duplicate_queue_number_raises(self, mock_db):
        mock_db.execute.side_effect = [
            make_scalar_result(None),     # name check passes
            make_scalar_result(_make_queue()),  # queue_number check fails
        ]
        data = QueueCreate(name="Different Name", queue_number="800")

        service = QueueService(mock_db)
        with pytest.raises(ValueError, match="already exists"):
            await service.create_queue(TENANT_ACME_ID, data)


class TestUpdateQueue:
    async def test_success(self, mock_db):
        queue = _make_queue()
        mock_db.execute.return_value = make_scalar_result(queue)
        data = QueueUpdate(description="Updated desc")

        service = QueueService(mock_db)
        await service.update_queue(TENANT_ACME_ID, queue.id, data)
        assert queue.description == "Updated desc"
        mock_db.commit.assert_awaited_once()

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = QueueService(mock_db)
        with pytest.raises(ValueError, match="Queue not found"):
            await service.update_queue(
                TENANT_ACME_ID, uuid.uuid4(), QueueUpdate(description="x")
            )


class TestDeactivateQueue:
    async def test_success(self, mock_db):
        queue = _make_queue()
        mock_db.execute.return_value = make_scalar_result(queue)

        service = QueueService(mock_db)
        await service.deactivate(TENANT_ACME_ID, queue.id)
        assert queue.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = QueueService(mock_db)
        with pytest.raises(ValueError, match="Queue not found"):
            await service.deactivate(TENANT_ACME_ID, uuid.uuid4())

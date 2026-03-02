import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_phone.db.rls import set_tenant_context
from new_phone.models.extension import Extension
from new_phone.models.queue import Queue, QueueMember
from new_phone.schemas.queue import QueueCreate, QueueUpdate

logger = structlog.get_logger()


class QueueService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_queues(self, tenant_id: uuid.UUID) -> list[Queue]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Queue)
            .where(Queue.tenant_id == tenant_id, Queue.is_active.is_(True))
            .options(selectinload(Queue.members))
            .order_by(Queue.name)
        )
        return list(result.scalars().all())

    async def get_queue(self, tenant_id: uuid.UUID, queue_id: uuid.UUID) -> Queue | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Queue)
            .where(Queue.id == queue_id, Queue.tenant_id == tenant_id, Queue.is_active.is_(True))
            .options(selectinload(Queue.members))
        )
        return result.scalar_one_or_none()

    async def create_queue(self, tenant_id: uuid.UUID, data: QueueCreate) -> Queue:
        await set_tenant_context(self.db, tenant_id)

        # Check duplicate name
        existing = await self.db.execute(
            select(Queue).where(
                Queue.tenant_id == tenant_id,
                Queue.name == data.name,
                Queue.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Queue '{data.name}' already exists")

        # Check duplicate queue_number
        existing = await self.db.execute(
            select(Queue).where(
                Queue.tenant_id == tenant_id,
                Queue.queue_number == data.queue_number,
                Queue.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Queue number '{data.queue_number}' already exists")

        queue = Queue(
            tenant_id=tenant_id,
            name=data.name,
            queue_number=data.queue_number,
            description=data.description,
            strategy=data.strategy,
            moh_prompt_id=data.moh_prompt_id,
            max_wait_time=data.max_wait_time,
            max_wait_time_with_no_agent=data.max_wait_time_with_no_agent,
            tier_rules_apply=data.tier_rules_apply,
            tier_rule_wait_second=data.tier_rule_wait_second,
            tier_rule_wait_multiply_level=data.tier_rule_wait_multiply_level,
            tier_rule_no_agent_no_wait=data.tier_rule_no_agent_no_wait,
            discard_abandoned_after=data.discard_abandoned_after,
            abandoned_resume_allowed=data.abandoned_resume_allowed,
            caller_exit_key=data.caller_exit_key,
            wrapup_time=data.wrapup_time,
            ring_timeout=data.ring_timeout,
            announce_frequency=data.announce_frequency,
            announce_prompt_id=data.announce_prompt_id,
            overflow_destination_type=data.overflow_destination_type,
            overflow_destination_id=data.overflow_destination_id,
            record_calls=data.record_calls,
            enabled=data.enabled,
        )
        self.db.add(queue)
        await self.db.flush()

        # Create members
        for m in data.members:
            member = QueueMember(
                queue_id=queue.id,
                extension_id=m.extension_id,
                level=m.level,
                position=m.position,
            )
            self.db.add(member)

        await self.db.commit()
        await self.db.refresh(queue)
        return queue

    async def update_queue(self, tenant_id: uuid.UUID, queue_id: uuid.UUID, data: QueueUpdate) -> Queue:
        queue = await self.get_queue(tenant_id, queue_id)
        if not queue:
            raise ValueError("Queue not found")

        update_data = data.model_dump(exclude_unset=True)
        members_data = update_data.pop("members", None)

        # Check name uniqueness if changing
        if "name" in update_data and update_data["name"] != queue.name:
            existing = await self.db.execute(
                select(Queue).where(
                    Queue.tenant_id == tenant_id,
                    Queue.name == update_data["name"],
                    Queue.is_active.is_(True),
                    Queue.id != queue_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Queue '{update_data['name']}' already exists")

        # Check queue_number uniqueness if changing
        if "queue_number" in update_data and update_data["queue_number"] != queue.queue_number:
            existing = await self.db.execute(
                select(Queue).where(
                    Queue.tenant_id == tenant_id,
                    Queue.queue_number == update_data["queue_number"],
                    Queue.is_active.is_(True),
                    Queue.id != queue_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Queue number '{update_data['queue_number']}' already exists")

        for key, value in update_data.items():
            setattr(queue, key, value)

        # Replace members wholesale if provided
        if members_data is not None:
            for m in list(queue.members):
                await self.db.delete(m)
            await self.db.flush()
            for m_data in data.members:
                member = QueueMember(
                    queue_id=queue.id,
                    extension_id=m_data.extension_id,
                    level=m_data.level,
                    position=m_data.position,
                )
                self.db.add(member)

        await self.db.commit()
        await self.db.refresh(queue)
        return queue

    async def deactivate(self, tenant_id: uuid.UUID, queue_id: uuid.UUID) -> Queue:
        queue = await self.get_queue(tenant_id, queue_id)
        if not queue:
            raise ValueError("Queue not found")
        queue.is_active = False
        await self.db.commit()
        await self.db.refresh(queue)
        return queue

    async def set_agent_status(
        self,
        tenant_id: uuid.UUID,
        queue_id: uuid.UUID,
        extension_id: uuid.UUID,
        status: str,
    ) -> Extension:
        """Set agent status in DB. Caller is responsible for ESL sync."""
        await set_tenant_context(self.db, tenant_id)

        # Verify queue exists and agent is a member
        queue = await self.get_queue(tenant_id, queue_id)
        if not queue:
            raise ValueError("Queue not found")

        member = None
        for m in queue.members:
            if m.extension_id == extension_id:
                member = m
                break
        if not member:
            raise ValueError("Extension is not a member of this queue")

        # Update extension agent_status
        result = await self.db.execute(
            select(Extension).where(
                Extension.id == extension_id,
                Extension.tenant_id == tenant_id,
                Extension.is_active.is_(True),
            )
        )
        ext = result.scalar_one_or_none()
        if not ext:
            raise ValueError("Extension not found")

        ext.agent_status = status
        await self.db.commit()
        await self.db.refresh(ext)
        return ext

    async def get_agent_statuses(self, tenant_id: uuid.UUID) -> list[Extension]:
        """Get all extensions that are queue agents (have agent_status set)."""
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Extension).where(
                Extension.tenant_id == tenant_id,
                Extension.is_active.is_(True),
                Extension.agent_status.isnot(None),
            )
        )
        return list(result.scalars().all())

    async def get_queue_stats(
        self, tenant_id: uuid.UUID, queue_id: uuid.UUID
    ) -> dict:
        """Get real-time stats for a queue from DB (FS ESL query done in router)."""
        queue = await self.get_queue(tenant_id, queue_id)
        if not queue:
            raise ValueError("Queue not found")

        # Count agents by status from DB
        agents_logged_in = 0
        agents_available = 0
        for m in queue.members:
            ext = m.extension
            if ext and ext.is_active:
                status = ext.agent_status
                if status and status != "Logged Out":
                    agents_logged_in += 1
                if status == "Available":
                    agents_available += 1

        return {
            "queue_id": queue.id,
            "queue_name": queue.name,
            "waiting_count": 0,  # Would come from ESL query
            "agents_logged_in": agents_logged_in,
            "agents_available": agents_available,
            "agents_on_call": 0,  # Would come from ESL query
            "longest_wait_seconds": 0,  # Would come from ESL query
        }

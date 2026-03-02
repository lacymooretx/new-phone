import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.tenant import Tenant
from new_phone.models.user import User
from new_phone.schemas.queue import (
    AgentStatusResponse,
    AgentStatusUpdate,
    QueueCreate,
    QueueResponse,
    QueueStatsResponse,
    QueueUpdate,
)
from new_phone.services.queue_service import QueueService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/queues", tags=["queues"])


async def _sync_queue_change() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_queue_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ── Queue CRUD ──


@router.get("", response_model=list[QueueResponse])
async def list_queues(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = QueueService(db)
    return await service.list_queues(tenant_id)


@router.post("", response_model=QueueResponse, status_code=status.HTTP_201_CREATED)
async def create_queue(
    tenant_id: uuid.UUID,
    body: QueueCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = QueueService(db)
    try:
        queue = await service.create_queue(tenant_id, body)
        await _sync_queue_change()
        return queue
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/agent-status", response_model=list[AgentStatusResponse])
async def get_agent_statuses(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = QueueService(db)
    extensions = await service.get_agent_statuses(tenant_id)
    return [
        AgentStatusResponse(
            extension_id=ext.id,
            extension_number=ext.extension_number,
            agent_status=ext.agent_status,
        )
        for ext in extensions
    ]


@router.get("/stats", response_model=list[QueueStatsResponse])
async def get_all_queue_stats(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = QueueService(db)
    queues = await service.list_queues(tenant_id)
    stats = []
    for q in queues:
        s = await service.get_queue_stats(tenant_id, q.id)
        stats.append(QueueStatsResponse(**s))
    return stats


@router.get("/{queue_id}", response_model=QueueResponse)
async def get_queue(
    tenant_id: uuid.UUID,
    queue_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = QueueService(db)
    queue = await service.get_queue(tenant_id, queue_id)
    if not queue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue not found")
    return queue


@router.patch("/{queue_id}", response_model=QueueResponse)
async def update_queue(
    tenant_id: uuid.UUID,
    queue_id: uuid.UUID,
    body: QueueUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = QueueService(db)
    try:
        queue = await service.update_queue(tenant_id, queue_id, body)
        await _sync_queue_change()
        return queue
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{queue_id}", response_model=QueueResponse)
async def deactivate_queue(
    tenant_id: uuid.UUID,
    queue_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = QueueService(db)
    try:
        queue = await service.deactivate(tenant_id, queue_id)
        await _sync_queue_change()
        return queue
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ── Agent Status ──


@router.put("/{queue_id}/agents/{extension_id}/status", response_model=AgentStatusResponse)
async def set_agent_status(
    tenant_id: uuid.UUID,
    queue_id: uuid.UUID,
    extension_id: uuid.UUID,
    body: AgentStatusUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = QueueService(db)
    try:
        ext = await service.set_agent_status(tenant_id, queue_id, extension_id, body.status)
        # Sync to FreeSWITCH
        try:
            from new_phone.main import config_sync
            if config_sync:
                tenant_result = await db.execute(
                    sa_select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = tenant_result.scalar_one_or_none()
                if tenant:
                    domain = tenant.sip_domain or f"{tenant.slug}.sip.local"
                    agent_name = f"{ext.extension_number}@{domain}"
                    await config_sync.notify_agent_status_change(agent_name, body.status)
        except Exception as e:
            logger.warning("agent_status_sync_failed", error=str(e))

        return AgentStatusResponse(
            extension_id=ext.id,
            extension_number=ext.extension_number,
            agent_status=ext.agent_status,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ── Queue Stats ──


@router.get("/{queue_id}/stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    tenant_id: uuid.UUID,
    queue_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = QueueService(db)
    try:
        stats = await service.get_queue_stats(tenant_id, queue_id)
        return QueueStatsResponse(**stats)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None

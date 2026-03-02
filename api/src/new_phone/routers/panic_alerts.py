import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.panic_alert import (
    PanicAlertResolveRequest,
    PanicAlertResponse,
    PanicAlertTriggerRequest,
)
from new_phone.services.panic_alert_service import PanicAlertService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/panic-alerts", tags=["security"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post("", response_model=PanicAlertResponse, status_code=status.HTTP_201_CREATED)
async def trigger_panic_alert(
    tenant_id: uuid.UUID,
    body: PanicAlertTriggerRequest,
    user: Annotated[User, Depends(require_permission(Permission.TRIGGER_PANIC))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PanicAlertService(db)
    return await service.trigger_alert(tenant_id, user.id, body)


@router.get("", response_model=list[PanicAlertResponse])
async def list_panic_alerts(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_SECURITY))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    alert_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
):
    _check_tenant_access(user, tenant_id)
    service = PanicAlertService(db)
    return await service.list_alerts(tenant_id, status_filter=alert_status, limit=limit)


@router.get("/{alert_id}", response_model=PanicAlertResponse)
async def get_panic_alert(
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_SECURITY))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PanicAlertService(db)
    alert = await service.get_alert(tenant_id, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Panic alert not found")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=PanicAlertResponse)
async def acknowledge_panic_alert(
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PANIC_ALERTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PanicAlertService(db)
    try:
        return await service.acknowledge(tenant_id, alert_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.post("/{alert_id}/resolve", response_model=PanicAlertResponse)
async def resolve_panic_alert(
    tenant_id: uuid.UUID,
    alert_id: uuid.UUID,
    body: PanicAlertResolveRequest,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PANIC_ALERTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PanicAlertService(db)
    try:
        return await service.resolve(tenant_id, alert_id, user.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None

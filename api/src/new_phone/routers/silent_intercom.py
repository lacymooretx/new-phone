import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.silent_intercom import SilentIntercomResponse, SilentIntercomStartRequest
from new_phone.services.silent_intercom_service import SilentIntercomService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/silent-intercom", tags=["security"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post(
    "/sessions", response_model=SilentIntercomResponse, status_code=status.HTTP_201_CREATED
)
async def start_silent_intercom(
    tenant_id: uuid.UUID,
    body: SilentIntercomStartRequest,
    user: Annotated[User, Depends(require_permission(Permission.SECURITY_LISTEN))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SilentIntercomService(db)
    try:
        return await service.start_session(tenant_id, user.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from None


@router.get("/sessions", response_model=list[SilentIntercomResponse])
async def list_silent_intercom_sessions(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.SECURITY_LISTEN))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    limit: int = Query(50, ge=1, le=200),
):
    _check_tenant_access(user, tenant_id)
    service = SilentIntercomService(db)
    return await service.list_sessions(tenant_id, limit=limit)


@router.get("/sessions/{session_id}", response_model=SilentIntercomResponse)
async def get_silent_intercom_session(
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.SECURITY_LISTEN))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SilentIntercomService(db)
    session_record = await service.get_session(tenant_id, session_id)
    if not session_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session_record


@router.delete("/sessions/{session_id}", response_model=SilentIntercomResponse)
async def end_silent_intercom_session(
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.SECURITY_LISTEN))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SilentIntercomService(db)
    try:
        return await service.end_session(tenant_id, session_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None

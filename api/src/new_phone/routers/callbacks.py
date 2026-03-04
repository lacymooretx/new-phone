import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_db_with_tenant, require_permission
from new_phone.models.user import User
from new_phone.schemas.callback import (
    ScheduledCallbackCreate,
    ScheduledCallbackResponse,
    ScheduledCallbackUpdate,
)
from new_phone.services.callback_service import CallbackService

router = APIRouter(prefix="/tenants/{tenant_id}/callbacks", tags=["callbacks"])


@router.get("", response_model=dict)
async def list_callbacks(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    queue_id: Annotated[uuid.UUID | None, Query()] = None,
    callback_status: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
):
    service = CallbackService(db)
    items, total = await service.list_callbacks(tenant_id, queue_id, callback_status, page, per_page)
    return {
        "items": [ScheduledCallbackResponse.model_validate(cb) for cb in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("", response_model=ScheduledCallbackResponse, status_code=status.HTTP_201_CREATED)
async def create_callback(
    tenant_id: uuid.UUID,
    data: ScheduledCallbackCreate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
):
    service = CallbackService(db)
    return await service.create_callback(tenant_id, **data.model_dump())


@router.get("/{callback_id}", response_model=ScheduledCallbackResponse)
async def get_callback(
    tenant_id: uuid.UUID,
    callback_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
):
    service = CallbackService(db)
    cb = await service.get_callback(tenant_id, callback_id)
    if not cb:
        raise HTTPException(status_code=404, detail="Callback not found")
    return cb


@router.put("/{callback_id}", response_model=ScheduledCallbackResponse)
async def update_callback(
    tenant_id: uuid.UUID,
    callback_id: uuid.UUID,
    data: ScheduledCallbackUpdate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
):
    service = CallbackService(db)
    cb = await service.update_callback(tenant_id, callback_id, **data.model_dump(exclude_unset=True))
    if not cb:
        raise HTTPException(status_code=404, detail="Callback not found")
    return cb


@router.post("/{callback_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_callback(
    tenant_id: uuid.UUID,
    callback_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
):
    service = CallbackService(db)
    cancelled = await service.cancel_callback(tenant_id, callback_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Callback not found or already completed")

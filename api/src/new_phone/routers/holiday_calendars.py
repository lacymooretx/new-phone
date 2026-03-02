import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.holiday_calendar import (
    HolidayCalendarCreate,
    HolidayCalendarResponse,
    HolidayCalendarUpdate,
)
from new_phone.services.holiday_calendar_service import HolidayCalendarService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/holiday-calendars", tags=["holiday-calendars"])


async def _sync_dialplan() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_dialplan_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[HolidayCalendarResponse])
async def list_holiday_calendars(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HolidayCalendarService(db)
    return await service.list_calendars(tenant_id)


@router.post("", response_model=HolidayCalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_holiday_calendar(
    tenant_id: uuid.UUID,
    body: HolidayCalendarCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HolidayCalendarService(db)
    try:
        calendar = await service.create_calendar(tenant_id, body)
        await _sync_dialplan()
        return calendar
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{calendar_id}", response_model=HolidayCalendarResponse)
async def get_holiday_calendar(
    tenant_id: uuid.UUID,
    calendar_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HolidayCalendarService(db)
    calendar = await service.get_calendar(tenant_id, calendar_id)
    if not calendar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday calendar not found")
    return calendar


@router.patch("/{calendar_id}", response_model=HolidayCalendarResponse)
async def update_holiday_calendar(
    tenant_id: uuid.UUID,
    calendar_id: uuid.UUID,
    body: HolidayCalendarUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HolidayCalendarService(db)
    try:
        calendar = await service.update_calendar(tenant_id, calendar_id, body)
        await _sync_dialplan()
        return calendar
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{calendar_id}", response_model=HolidayCalendarResponse)
async def deactivate_holiday_calendar(
    tenant_id: uuid.UUID,
    calendar_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HolidayCalendarService(db)
    try:
        calendar = await service.deactivate(tenant_id, calendar_id)
        await _sync_dialplan()
        return calendar
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None

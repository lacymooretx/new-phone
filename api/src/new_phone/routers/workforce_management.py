import uuid
from datetime import date
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.workforce_management import (
    WfmDailyVolume,
    WfmForecastConfigCreate,
    WfmForecastConfigResponse,
    WfmForecastPoint,
    WfmHourlyVolume,
    WfmScheduleEntryBulkCreate,
    WfmScheduleEntryCreate,
    WfmScheduleEntryResponse,
    WfmScheduleEntryUpdate,
    WfmScheduleOverview,
    WfmShiftCreate,
    WfmShiftResponse,
    WfmShiftUpdate,
    WfmStaffingSummary,
    WfmTimeOffRequestCreate,
    WfmTimeOffRequestResponse,
    WfmTimeOffReview,
)
from new_phone.services.wfm_service import WfmService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/wfm", tags=["workforce-management"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _entry_response(entry) -> dict:
    """Build schedule entry response with denormalized extension fields."""
    ext = entry.extension
    return {
        **{c.key: getattr(entry, c.key) for c in entry.__table__.columns},
        "shift": entry.shift,
        "extension_number": ext.extension_number if ext else "",
        "extension_name": ext.internal_cid_name or ext.extension_number if ext else "",
    }


def _time_off_response(req) -> dict:
    """Build time-off request response with denormalized extension fields."""
    ext = req.extension
    return {
        **{c.key: getattr(req, c.key) for c in req.__table__.columns},
        "extension_number": ext.extension_number if ext else "",
        "extension_name": ext.internal_cid_name or ext.extension_number if ext else "",
    }


def _forecast_config_response(config) -> dict:
    """Build forecast config response with queue name."""
    queue = config.queue
    return {
        **{c.key: getattr(config, c.key) for c in config.__table__.columns},
        "queue_name": queue.name if queue else "",
    }


# ── Shifts ──


@router.get("/shifts", response_model=list[WfmShiftResponse])
async def list_shifts(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    is_active: bool | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    return await service.list_shifts(tenant_id, is_active=is_active)


@router.post("/shifts", response_model=WfmShiftResponse, status_code=status.HTTP_201_CREATED)
async def create_shift(
    tenant_id: uuid.UUID,
    body: WfmShiftCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    try:
        return await service.create_shift(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/shifts/{shift_id}", response_model=WfmShiftResponse)
async def get_shift(
    tenant_id: uuid.UUID,
    shift_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    shift = await service.get_shift(tenant_id, shift_id)
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    return shift


@router.patch("/shifts/{shift_id}", response_model=WfmShiftResponse)
async def update_shift(
    tenant_id: uuid.UUID,
    shift_id: uuid.UUID,
    body: WfmShiftUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    try:
        return await service.update_shift(tenant_id, shift_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/shifts/{shift_id}", response_model=WfmShiftResponse)
async def deactivate_shift(
    tenant_id: uuid.UUID,
    shift_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    try:
        return await service.deactivate_shift(tenant_id, shift_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ── Schedule ──


@router.get("/schedule", response_model=list[WfmScheduleEntryResponse])
async def list_schedule_entries(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: Annotated[date, Query()],
    date_to: Annotated[date, Query()],
    extension_id: uuid.UUID | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    entries = await service.list_schedule_entries(
        tenant_id, date_from=date_from, date_to=date_to, extension_id=extension_id
    )
    return [_entry_response(e) for e in entries]


@router.post("/schedule", response_model=WfmScheduleEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule_entry(
    tenant_id: uuid.UUID,
    body: WfmScheduleEntryCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    try:
        entry = await service.create_schedule_entry(tenant_id, body)
        return _entry_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.post("/schedule/bulk", response_model=list[WfmScheduleEntryResponse], status_code=status.HTTP_201_CREATED)
async def bulk_create_schedule_entries(
    tenant_id: uuid.UUID,
    body: WfmScheduleEntryBulkCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    try:
        entries = await service.bulk_create_schedule_entries(tenant_id, body.entries)
        return [_entry_response(e) for e in entries]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.patch("/schedule/{entry_id}", response_model=WfmScheduleEntryResponse)
async def update_schedule_entry(
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
    body: WfmScheduleEntryUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    try:
        entry = await service.update_schedule_entry(tenant_id, entry_id, body)
        return _entry_response(entry)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/schedule/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule_entry(
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    try:
        await service.delete_schedule_entry(tenant_id, entry_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.get("/schedule/overview", response_model=list[WfmScheduleOverview])
async def get_schedule_overview(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: Annotated[date, Query()],
    date_to: Annotated[date, Query()],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    return await service.get_schedule_overview(tenant_id, date_from, date_to)


# ── Time Off ──


@router.get("/time-off", response_model=list[WfmTimeOffRequestResponse])
async def list_time_off_requests(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    extension_id: uuid.UUID | None = None,
    request_status: Annotated[str | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    requests = await service.list_time_off_requests(
        tenant_id, extension_id=extension_id, status=request_status,
        date_from=date_from, date_to=date_to,
    )
    return [_time_off_response(r) for r in requests]


@router.post("/time-off", response_model=WfmTimeOffRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_time_off_request(
    tenant_id: uuid.UUID,
    body: WfmTimeOffRequestCreate,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    try:
        req = await service.create_time_off_request(tenant_id, body)
        return _time_off_response(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.patch("/time-off/{request_id}/review", response_model=WfmTimeOffRequestResponse)
async def review_time_off_request(
    tenant_id: uuid.UUID,
    request_id: uuid.UUID,
    body: WfmTimeOffReview,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    try:
        req = await service.review_time_off_request(tenant_id, request_id, user.id, body)
        return _time_off_response(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


# ── Forecast Config ──


@router.get("/forecast/configs", response_model=list[WfmForecastConfigResponse])
async def list_forecast_configs(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    configs = await service.list_forecast_configs(tenant_id)
    return [_forecast_config_response(c) for c in configs]


@router.put("/forecast/configs/{queue_id}", response_model=WfmForecastConfigResponse)
async def upsert_forecast_config(
    tenant_id: uuid.UUID,
    queue_id: uuid.UUID,
    body: WfmForecastConfigCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    # Ensure queue_id in body matches path
    body.queue_id = queue_id
    service = WfmService(db)
    config = await service.upsert_forecast_config(tenant_id, body)
    return _forecast_config_response(config)


# ── Analytics ──


@router.get("/analytics/hourly-volume", response_model=list[WfmHourlyVolume])
async def get_hourly_volume(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    queue_id: Annotated[uuid.UUID, Query()],
    date_from: Annotated[date, Query()],
    date_to: Annotated[date, Query()],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    return await service.get_hourly_volume(tenant_id, queue_id, date_from, date_to)


@router.get("/analytics/daily-volume", response_model=list[WfmDailyVolume])
async def get_daily_volume(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    queue_id: Annotated[uuid.UUID, Query()],
    date_from: Annotated[date, Query()],
    date_to: Annotated[date, Query()],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    return await service.get_daily_volume(tenant_id, queue_id, date_from, date_to)


# ── Forecast ──


@router.get("/forecast/summary", response_model=list[WfmStaffingSummary])
async def get_staffing_summary(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    return await service.get_staffing_summary(tenant_id)


@router.get("/forecast/{queue_id}", response_model=list[WfmForecastPoint])
async def get_staffing_forecast(
    tenant_id: uuid.UUID,
    queue_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_WFM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = WfmService(db)
    return await service.get_staffing_forecast(tenant_id, queue_id)

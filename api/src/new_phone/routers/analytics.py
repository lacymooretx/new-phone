"""Analytics endpoints — CDR aggregation for tenant dashboards and MSP overview."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.analytics import (
    CallSummary,
    CallVolumeTrendResponse,
    DIDUsage,
    DurationBucket,
    ExtensionActivity,
    HourlyDistributionPoint,
    MSPOverviewResponse,
    TopCaller,
)
from new_phone.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/tenants/{tenant_id}/analytics", tags=["analytics"])
msp_router = APIRouter(prefix="/analytics", tags=["analytics"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ── Tenant-scoped endpoints ────────────────────────────────────────────────────

@router.get("/summary", response_model=CallSummary)
async def get_call_summary(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = AnalyticsService(db)
    data = await service.get_call_summary(tenant_id, date_from, date_to)
    return CallSummary(**data)


@router.get("/volume-trend", response_model=CallVolumeTrendResponse)
async def get_call_volume_trend(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    granularity: str = "daily",
):
    _check_tenant_access(user, tenant_id)
    if granularity not in ("daily", "hourly"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="granularity must be 'daily' or 'hourly'",
        )
    service = AnalyticsService(db)
    data = await service.get_call_volume_trend(tenant_id, date_from, date_to, granularity)
    return CallVolumeTrendResponse(**data)


@router.get("/extension-activity", response_model=list[ExtensionActivity])
async def get_extension_activity(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(20, ge=1, le=100),
):
    _check_tenant_access(user, tenant_id)
    service = AnalyticsService(db)
    rows = await service.get_extension_activity(tenant_id, date_from, date_to, limit)
    return [ExtensionActivity(**r) for r in rows]


@router.get("/did-usage", response_model=list[DIDUsage])
async def get_did_usage(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(20, ge=1, le=100),
):
    _check_tenant_access(user, tenant_id)
    service = AnalyticsService(db)
    rows = await service.get_did_usage(tenant_id, date_from, date_to, limit)
    return [DIDUsage(**r) for r in rows]


@router.get("/duration-distribution", response_model=list[DurationBucket])
async def get_duration_distribution(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = AnalyticsService(db)
    rows = await service.get_duration_distribution(tenant_id, date_from, date_to)
    return [DurationBucket(**r) for r in rows]


@router.get("/top-callers", response_model=list[TopCaller])
async def get_top_callers(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(20, ge=1, le=100),
):
    _check_tenant_access(user, tenant_id)
    service = AnalyticsService(db)
    rows = await service.get_top_callers(tenant_id, date_from, date_to, limit)
    return [TopCaller(**r) for r in rows]


@router.get("/hourly-distribution", response_model=list[HourlyDistributionPoint])
async def get_hourly_distribution(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = AnalyticsService(db)
    rows = await service.get_hourly_distribution(tenant_id, date_from, date_to)
    return [HourlyDistributionPoint(**r) for r in rows]


# ── MSP-only endpoint ──────────────────────────────────────────────────────────

@msp_router.get("/msp-overview", response_model=MSPOverviewResponse)
async def get_msp_overview(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_ALL_TENANTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = AnalyticsService(db)
    data = await service.get_msp_overview()
    return MSPOverviewResponse(**data)

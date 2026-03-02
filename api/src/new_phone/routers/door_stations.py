import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.door_station import (
    DoorAccessLogResponse,
    DoorStationCreate,
    DoorStationResponse,
    DoorStationUpdate,
)
from new_phone.services.door_station_service import DoorStationService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/door-stations", tags=["security"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[DoorStationResponse])
async def list_door_stations(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DOOR_STATIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DoorStationService(db)
    return await service.list_door_stations(tenant_id)


@router.post("", response_model=DoorStationResponse, status_code=status.HTTP_201_CREATED)
async def create_door_station(
    tenant_id: uuid.UUID,
    body: DoorStationCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DOOR_STATIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DoorStationService(db)
    try:
        return await service.create_door_station(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{door_station_id}", response_model=DoorStationResponse)
async def get_door_station(
    tenant_id: uuid.UUID,
    door_station_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DOOR_STATIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DoorStationService(db)
    door_station = await service.get_door_station(tenant_id, door_station_id)
    if not door_station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Door station not found")
    return door_station


@router.patch("/{door_station_id}", response_model=DoorStationResponse)
async def update_door_station(
    tenant_id: uuid.UUID,
    door_station_id: uuid.UUID,
    body: DoorStationUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DOOR_STATIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DoorStationService(db)
    try:
        return await service.update_door_station(tenant_id, door_station_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{door_station_id}", response_model=DoorStationResponse)
async def deactivate_door_station(
    tenant_id: uuid.UUID,
    door_station_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DOOR_STATIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DoorStationService(db)
    try:
        return await service.deactivate_door_station(tenant_id, door_station_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.post(
    "/{door_station_id}/unlock",
    response_model=DoorAccessLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_door_unlock(
    tenant_id: uuid.UUID,
    door_station_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.TRIGGER_DOOR_UNLOCK))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DoorStationService(db)
    try:
        return await service.trigger_unlock(tenant_id, door_station_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.get("/{door_station_id}/access-logs", response_model=list[DoorAccessLogResponse])
async def list_door_access_logs(
    tenant_id: uuid.UUID,
    door_station_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DOOR_STATIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    limit: int = Query(50, ge=1, le=200),
):
    _check_tenant_access(user, tenant_id)
    service = DoorStationService(db)
    return await service.list_access_logs(tenant_id, door_station_id, limit=limit)

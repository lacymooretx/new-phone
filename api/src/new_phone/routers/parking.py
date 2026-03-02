import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.parking_lot import (
    ParkingLotCreate,
    ParkingLotResponse,
    ParkingLotUpdate,
    SlotState,
)
from new_phone.services.parking_service import ParkingService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/parking-lots", tags=["parking"])


async def _sync_parking_change() -> None:
    try:
        from new_phone.main import config_sync

        if config_sync:
            await config_sync.notify_parking_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[ParkingLotResponse])
async def list_parking_lots(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    site_id: uuid.UUID | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = ParkingService(db)
    return await service.list_lots(tenant_id, site_id=site_id)


@router.post("", response_model=ParkingLotResponse, status_code=status.HTTP_201_CREATED)
async def create_parking_lot(
    tenant_id: uuid.UUID,
    body: ParkingLotCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ParkingService(db)
    try:
        lot = await service.create_lot(tenant_id, body)
        await _sync_parking_change()
        return lot
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/slots", response_model=list[SlotState])
async def get_all_slot_states(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
):
    _check_tenant_access(user, tenant_id)
    return await ParkingService.get_slot_states(tenant_id)


@router.get("/{lot_id}", response_model=ParkingLotResponse)
async def get_parking_lot(
    tenant_id: uuid.UUID,
    lot_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ParkingService(db)
    lot = await service.get_lot(tenant_id, lot_id)
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking lot not found")
    return lot


@router.patch("/{lot_id}", response_model=ParkingLotResponse)
async def update_parking_lot(
    tenant_id: uuid.UUID,
    lot_id: uuid.UUID,
    body: ParkingLotUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ParkingService(db)
    try:
        lot = await service.update_lot(tenant_id, lot_id, body)
        await _sync_parking_change()
        return lot
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{lot_id}", response_model=ParkingLotResponse)
async def deactivate_parking_lot(
    tenant_id: uuid.UUID,
    lot_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ParkingService(db)
    try:
        lot = await service.deactivate(tenant_id, lot_id)
        await _sync_parking_change()
        return lot
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.get("/{lot_id}/slots", response_model=list[SlotState])
async def get_lot_slot_states(
    tenant_id: uuid.UUID,
    lot_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ParkingService(db)
    lot = await service.get_lot(tenant_id, lot_id)
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking lot not found")
    return await ParkingService.get_lot_slot_states(tenant_id, lot)

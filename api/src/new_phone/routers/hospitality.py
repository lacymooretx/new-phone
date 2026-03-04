import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.hospitality import (
    RoomCheckIn,
    RoomCreate,
    RoomResponse,
    RoomUpdate,
    WakeUpCallCreate,
    WakeUpCallResponse,
)
from new_phone.services.hospitality_service import HospitalityService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/hospitality", tags=["hospitality"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# --- Room endpoints ---


@router.get("/rooms", response_model=list[RoomResponse])
async def list_rooms(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    room_status: str | None = None,
    floor: str | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = HospitalityService(db)
    return await service.list_rooms(tenant_id, status=room_status, floor=floor)


@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    tenant_id: uuid.UUID,
    body: RoomCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HospitalityService(db)
    try:
        return await service.create_room(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room(
    tenant_id: uuid.UUID,
    room_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HospitalityService(db)
    room = await service.get_room(tenant_id, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


@router.patch("/rooms/{room_id}", response_model=RoomResponse)
async def update_room(
    tenant_id: uuid.UUID,
    room_id: uuid.UUID,
    body: RoomUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HospitalityService(db)
    try:
        return await service.update_room(tenant_id, room_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.post("/rooms/{room_id}/check-in", response_model=RoomResponse)
async def check_in(
    tenant_id: uuid.UUID,
    room_id: uuid.UUID,
    body: RoomCheckIn,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HospitalityService(db)
    try:
        return await service.check_in(
            tenant_id, room_id, body.guest_name, body.guest_checkout_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.post("/rooms/{room_id}/check-out", response_model=RoomResponse)
async def check_out(
    tenant_id: uuid.UUID,
    room_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HospitalityService(db)
    try:
        return await service.check_out(tenant_id, room_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# --- Wake-up call endpoints ---


@router.get("/rooms/{room_id}/wake-up-calls", response_model=list[WakeUpCallResponse])
async def list_wake_up_calls(
    tenant_id: uuid.UUID,
    room_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HospitalityService(db)
    return await service.list_wake_up_calls(tenant_id, room_id)


@router.post(
    "/rooms/{room_id}/wake-up-calls",
    response_model=WakeUpCallResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_wake_up_call(
    tenant_id: uuid.UUID,
    room_id: uuid.UUID,
    body: WakeUpCallCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HospitalityService(db)
    try:
        return await service.create_wake_up_call(tenant_id, room_id, body.scheduled_time)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.post("/wake-up-calls/{wake_up_id}/cancel", response_model=WakeUpCallResponse)
async def cancel_wake_up_call(
    tenant_id: uuid.UUID,
    wake_up_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = HospitalityService(db)
    try:
        return await service.cancel_wake_up_call(tenant_id, wake_up_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None

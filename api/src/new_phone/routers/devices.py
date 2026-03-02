import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.phone_apps.service import PhoneAppConfigService
from new_phone.schemas.device import (
    DeviceCreate,
    DeviceKeyBulkUpdate,
    DeviceKeyResponse,
    DeviceResponse,
    DeviceUpdate,
)
from new_phone.schemas.phone_app_config import PhoneAppConfigResponse, PhoneAppConfigUpdate
from new_phone.services.audit_utils import log_audit
from new_phone.services.device_service import DeviceService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/devices", tags=["devices"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DeviceService(db)
    devices = await service.list_devices(tenant_id)
    return [DeviceResponse.from_device(d) for d in devices]


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    tenant_id: uuid.UUID,
    body: DeviceCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DeviceService(db)
    try:
        device = await service.create_device(tenant_id, body)
        await log_audit(db, user, request, "create", "device", device.id)
        return DeviceResponse.from_device(device)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    tenant_id: uuid.UUID,
    device_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DeviceService(db)
    device = await service.get_device(tenant_id, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceResponse.from_device(device)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    tenant_id: uuid.UUID,
    device_id: uuid.UUID,
    body: DeviceUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DeviceService(db)
    try:
        device = await service.update_device(tenant_id, device_id, body)
        await log_audit(db, user, request, "update", "device", device.id)
        return DeviceResponse.from_device(device)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{device_id}", response_model=DeviceResponse)
async def deactivate_device(
    tenant_id: uuid.UUID,
    device_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DeviceService(db)
    try:
        device = await service.deactivate_device(tenant_id, device_id)
        await log_audit(db, user, request, "delete", "device", device.id)
        return DeviceResponse.from_device(device)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.get("/{device_id}/keys", response_model=list[DeviceKeyResponse])
async def get_device_keys(
    tenant_id: uuid.UUID,
    device_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DeviceService(db)
    return await service.get_device_keys(tenant_id, device_id)


@router.put("/{device_id}/keys", response_model=list[DeviceKeyResponse])
async def update_device_keys(
    tenant_id: uuid.UUID,
    device_id: uuid.UUID,
    body: DeviceKeyBulkUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DeviceService(db)
    try:
        keys = await service.bulk_update_keys(tenant_id, device_id, body.keys)
        await log_audit(db, user, request, "update", "device_keys", device_id)
        return keys
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ── Phone App Config ────────────────────────────────────────────────


@router.get("/phone-app-config", response_model=PhoneAppConfigResponse)
async def get_phone_app_config(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PhoneAppConfigService(db)
    config = await service.get_or_create(tenant_id)
    await db.commit()
    return config


@router.patch("/phone-app-config", response_model=PhoneAppConfigResponse)
async def update_phone_app_config(
    tenant_id: uuid.UUID,
    body: PhoneAppConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = PhoneAppConfigService(db)
    config = await service.update(tenant_id, body)
    await log_audit(db, user, request, "update", "phone_app_config", config.id)
    await db.commit()
    return config

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.stir_shaken import (
    NumberCheckRequest,
    NumberCheckResult,
    SpamAllowListCreate,
    SpamAllowListResponse,
    SpamBlockListCreate,
    SpamBlockListResponse,
    SpamFilterCreate,
    SpamFilterResponse,
    SpamFilterUpdate,
    StirShakenConfigCreate,
    StirShakenConfigResponse,
    StirShakenConfigUpdate,
)
from new_phone.services.stir_shaken_service import StirShakenService

router = APIRouter(
    prefix="/tenants/{tenant_id}/stir-shaken",
    tags=["stir-shaken"],
)


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ── STIR/SHAKEN Config ──


@router.get("/config", response_model=StirShakenConfigResponse)
async def get_config(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    config = await service.get_config(tenant_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="STIR/SHAKEN config not found"
        )
    return config


@router.post(
    "/config",
    response_model=StirShakenConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_config(
    tenant_id: uuid.UUID,
    body: StirShakenConfigCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    existing = await service.get_config(tenant_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="STIR/SHAKEN config already exists for this tenant",
        )
    return await service.create_config(tenant_id, body)


@router.patch("/config", response_model=StirShakenConfigResponse)
async def update_config(
    tenant_id: uuid.UUID,
    body: StirShakenConfigUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    try:
        return await service.update_config(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    await service.delete_config(tenant_id)


# ── Spam Filters ──


@router.get("/spam-filters", response_model=list[SpamFilterResponse])
async def list_spam_filters(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    return await service.list_spam_filters(tenant_id)


@router.get("/spam-filters/{filter_id}", response_model=SpamFilterResponse)
async def get_spam_filter(
    tenant_id: uuid.UUID,
    filter_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    spam_filter = await service.get_spam_filter(tenant_id, filter_id)
    if not spam_filter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Spam filter not found"
        )
    return spam_filter


@router.post(
    "/spam-filters",
    response_model=SpamFilterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_spam_filter(
    tenant_id: uuid.UUID,
    body: SpamFilterCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    return await service.create_spam_filter(tenant_id, body)


@router.patch("/spam-filters/{filter_id}", response_model=SpamFilterResponse)
async def update_spam_filter(
    tenant_id: uuid.UUID,
    filter_id: uuid.UUID,
    body: SpamFilterUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    try:
        return await service.update_spam_filter(tenant_id, filter_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/spam-filters/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spam_filter(
    tenant_id: uuid.UUID,
    filter_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    try:
        await service.delete_spam_filter(tenant_id, filter_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ── Spam Block List ──


@router.get("/block-list", response_model=list[SpamBlockListResponse])
async def list_blocked_numbers(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    return await service.list_blocked_numbers(tenant_id)


@router.post(
    "/block-list",
    response_model=SpamBlockListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_blocked_number(
    tenant_id: uuid.UUID,
    body: SpamBlockListCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    try:
        return await service.add_blocked_number(tenant_id, body)
    except Exception as e:
        if "uq_spam_block_list_tenant_phone" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already blocked",
            ) from None
        raise


@router.delete("/block-list/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_blocked_number(
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    try:
        await service.remove_blocked_number(tenant_id, entry_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ── Spam Allow List ──


@router.get("/allow-list", response_model=list[SpamAllowListResponse])
async def list_allowed_numbers(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    return await service.list_allowed_numbers(tenant_id)


@router.post(
    "/allow-list",
    response_model=SpamAllowListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_allowed_number(
    tenant_id: uuid.UUID,
    body: SpamAllowListCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    try:
        return await service.add_allowed_number(tenant_id, body)
    except Exception as e:
        if "uq_spam_allow_list_tenant_phone" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already in allow list",
            ) from None
        raise


@router.delete("/allow-list/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_allowed_number(
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    try:
        await service.remove_allowed_number(tenant_id, entry_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ── Number Check ──


@router.post("/check-number", response_model=NumberCheckResult)
async def check_number(
    tenant_id: uuid.UUID,
    body: NumberCheckRequest,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = StirShakenService(db)
    return await service.check_number(tenant_id, body.phone_number)

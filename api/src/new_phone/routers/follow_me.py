import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.follow_me import FollowMeResponse, FollowMeUpdate
from new_phone.services.follow_me_service import FollowMeService

logger = structlog.get_logger()


async def _sync_dialplan() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_dialplan_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))

router = APIRouter(
    prefix="/tenants/{tenant_id}/extensions/{ext_id}/follow-me",
    tags=["follow-me"],
)


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=FollowMeResponse | dict)
async def get_follow_me(
    tenant_id: uuid.UUID,
    ext_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = FollowMeService(db)
    fm = await service.get_follow_me(tenant_id, ext_id)
    if not fm:
        # Return empty default
        return {
            "id": None,
            "tenant_id": tenant_id,
            "extension_id": ext_id,
            "enabled": False,
            "strategy": "sequential",
            "ring_extension_first": True,
            "extension_ring_time": 25,
            "destinations": [],
            "is_active": True,
            "created_at": None,
            "updated_at": None,
        }
    return fm


@router.put("", response_model=FollowMeResponse)
async def upsert_follow_me(
    tenant_id: uuid.UUID,
    ext_id: uuid.UUID,
    body: FollowMeUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_EXTENSIONS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = FollowMeService(db)
    fm = await service.upsert_follow_me(tenant_id, ext_id, body)
    await _sync_dialplan()
    return fm

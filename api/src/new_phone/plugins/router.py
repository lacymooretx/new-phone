import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_current_user, get_db_with_tenant, require_permission
from new_phone.models.user import User
from new_phone.plugins.schemas import (
    PluginEventLogResponse,
    PluginResponse,
    TenantPluginConfigUpdate,
    TenantPluginResponse,
)
from new_phone.plugins.service import PluginService

catalog_router = APIRouter(prefix="/plugins", tags=["plugins"])
tenant_router = APIRouter(prefix="/tenants/{tenant_id}/plugins", tags=["plugins"])


# ── Public Catalog ───────────────────────────────────────────────────


@catalog_router.get("", response_model=list[PluginResponse])
async def list_available_plugins(
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    _user: Annotated[User, Depends(get_current_user)],
):
    service = PluginService(db)
    return await service.list_available_plugins()


# ── Tenant-scoped ────────────────────────────────────────────────────


@tenant_router.get("", response_model=list[TenantPluginResponse])
async def list_installed_plugins(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    _user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = PluginService(db)
    return await service.list_installed_plugins(tenant_id)


@tenant_router.post(
    "/{plugin_id}/install",
    response_model=TenantPluginResponse,
    status_code=status.HTTP_201_CREATED,
)
async def install_plugin(
    tenant_id: uuid.UUID,
    plugin_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = PluginService(db)
    plugin = await service.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    try:
        return await service.install_plugin(tenant_id, plugin_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@tenant_router.post("/{plugin_id}/uninstall", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_plugin(
    tenant_id: uuid.UUID,
    plugin_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    _user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = PluginService(db)
    removed = await service.uninstall_plugin(tenant_id, plugin_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Plugin not installed")


@tenant_router.post("/{plugin_id}/activate", response_model=TenantPluginResponse)
async def activate_plugin(
    tenant_id: uuid.UUID,
    plugin_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    _user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = PluginService(db)
    tp = await service.activate_plugin(tenant_id, plugin_id)
    if not tp:
        raise HTTPException(status_code=404, detail="Plugin not installed")
    return tp


@tenant_router.post("/{plugin_id}/deactivate", response_model=TenantPluginResponse)
async def deactivate_plugin(
    tenant_id: uuid.UUID,
    plugin_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    _user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = PluginService(db)
    tp = await service.deactivate_plugin(tenant_id, plugin_id)
    if not tp:
        raise HTTPException(status_code=404, detail="Plugin not installed")
    return tp


@tenant_router.put("/{plugin_id}/config", response_model=TenantPluginResponse)
async def update_plugin_config(
    tenant_id: uuid.UUID,
    plugin_id: uuid.UUID,
    data: TenantPluginConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    _user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = PluginService(db)
    tp = await service.update_plugin_config(tenant_id, plugin_id, data.config)
    if not tp:
        raise HTTPException(status_code=404, detail="Plugin not installed")
    return tp


@tenant_router.get("/{plugin_id}/logs", response_model=dict)
async def list_plugin_event_logs(
    tenant_id: uuid.UUID,
    plugin_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    _user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
):
    service = PluginService(db)
    logs, total = await service.list_event_logs(tenant_id, plugin_id, page, per_page)
    return {
        "items": [PluginEventLogResponse.model_validate(log) for log in logs],
        "total": total,
        "page": page,
        "per_page": per_page,
    }

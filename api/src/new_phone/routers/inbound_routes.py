import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.inbound_route import (
    InboundRouteCreate,
    InboundRouteResponse,
    InboundRouteUpdate,
)
from new_phone.services.inbound_route_service import InboundRouteService

logger = structlog.get_logger()


async def _sync_dialplan() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_dialplan_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))

router = APIRouter(prefix="/tenants/{tenant_id}/inbound-routes", tags=["inbound-routes"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[InboundRouteResponse])
async def list_inbound_routes(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_INBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = InboundRouteService(db)
    return await service.list_inbound_routes(tenant_id)


@router.post("", response_model=InboundRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_inbound_route(
    tenant_id: uuid.UUID,
    body: InboundRouteCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_INBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = InboundRouteService(db)
    route = await service.create_inbound_route(tenant_id, body)
    await _sync_dialplan()
    return route


@router.get("/{route_id}", response_model=InboundRouteResponse)
async def get_inbound_route(
    tenant_id: uuid.UUID,
    route_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_INBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = InboundRouteService(db)
    route = await service.get_inbound_route(tenant_id, route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbound route not found")
    return route


@router.patch("/{route_id}", response_model=InboundRouteResponse)
async def update_inbound_route(
    tenant_id: uuid.UUID,
    route_id: uuid.UUID,
    body: InboundRouteUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_INBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = InboundRouteService(db)
    try:
        route = await service.update_inbound_route(tenant_id, route_id, body)
        await _sync_dialplan()
        return route
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{route_id}", response_model=InboundRouteResponse)
async def deactivate_inbound_route(
    tenant_id: uuid.UUID,
    route_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_INBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = InboundRouteService(db)
    try:
        route = await service.deactivate_inbound_route(tenant_id, route_id)
        await _sync_dialplan()
        return route
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None

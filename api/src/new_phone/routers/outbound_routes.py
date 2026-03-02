import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.outbound_route import (
    OutboundRouteCreate,
    OutboundRouteResponse,
    OutboundRouteUpdate,
)
from new_phone.services.outbound_route_service import OutboundRouteService

logger = structlog.get_logger()


async def _sync_dialplan() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_dialplan_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))

router = APIRouter(prefix="/tenants/{tenant_id}/outbound-routes", tags=["outbound-routes"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _route_to_response(route) -> dict:
    """Convert OutboundRoute ORM object to response dict with trunk_ids."""
    data = {
        "id": route.id,
        "tenant_id": route.tenant_id,
        "name": route.name,
        "dial_pattern": route.dial_pattern,
        "prepend_digits": route.prepend_digits,
        "strip_digits": route.strip_digits,
        "cid_mode": route.cid_mode,
        "custom_cid": route.custom_cid,
        "priority": route.priority,
        "enabled": route.enabled,
        "is_active": route.is_active,
        "trunk_ids": [a.trunk_id for a in route.trunk_assignments],
        "created_at": route.created_at,
        "updated_at": route.updated_at,
    }
    return data


@router.get("", response_model=list[OutboundRouteResponse])
async def list_outbound_routes(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_OUTBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = OutboundRouteService(db)
    routes = await service.list_outbound_routes(tenant_id)
    return [_route_to_response(r) for r in routes]


@router.post("", response_model=OutboundRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_outbound_route(
    tenant_id: uuid.UUID,
    body: OutboundRouteCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_OUTBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = OutboundRouteService(db)
    route = await service.create_outbound_route(tenant_id, body)
    await _sync_dialplan()
    return _route_to_response(route)


@router.get("/{route_id}", response_model=OutboundRouteResponse)
async def get_outbound_route(
    tenant_id: uuid.UUID,
    route_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_OUTBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = OutboundRouteService(db)
    route = await service.get_outbound_route(tenant_id, route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound route not found")
    return _route_to_response(route)


@router.patch("/{route_id}", response_model=OutboundRouteResponse)
async def update_outbound_route(
    tenant_id: uuid.UUID,
    route_id: uuid.UUID,
    body: OutboundRouteUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_OUTBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = OutboundRouteService(db)
    try:
        route = await service.update_outbound_route(tenant_id, route_id, body)
        await _sync_dialplan()
        return _route_to_response(route)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{route_id}", response_model=OutboundRouteResponse)
async def deactivate_outbound_route(
    tenant_id: uuid.UUID,
    route_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_OUTBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = OutboundRouteService(db)
    try:
        route = await service.deactivate_outbound_route(tenant_id, route_id)
        await _sync_dialplan()
        return _route_to_response(route)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None

"""Inter-tenant routing endpoints — MSP-only.

Prefix: /api/v1/inter-tenant-routes
Permission: MANAGE_PLATFORM
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.migration import InterTenantRoute
from new_phone.models.user import User
from new_phone.schemas.migration import InterTenantRouteCreate, InterTenantRouteResponse

logger = structlog.get_logger()

router = APIRouter(
    prefix="/inter-tenant-routes",
    tags=["inter-tenant-routes"],
)


@router.get("", response_model=list[InterTenantRouteResponse])
async def list_inter_tenant_routes(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """List all inter-tenant routes."""
    result = await db.execute(
        select(InterTenantRoute).order_by(InterTenantRoute.created_at.desc())
    )
    return [
        InterTenantRouteResponse.model_validate(r) for r in result.scalars().all()
    ]


@router.post(
    "",
    response_model=InterTenantRouteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_inter_tenant_route(
    body: InterTenantRouteCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Create a new inter-tenant route."""
    if body.source_tenant_id == body.target_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target tenants must be different",
        )

    # Check for duplicate prefix between the same tenant pair.
    existing = await db.execute(
        select(InterTenantRoute).where(
            InterTenantRoute.source_tenant_id == body.source_tenant_id,
            InterTenantRoute.target_tenant_id == body.target_tenant_id,
            InterTenantRoute.prefix == body.prefix,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Route with this prefix already exists between these tenants",
        )

    route = InterTenantRoute(
        source_tenant_id=body.source_tenant_id,
        target_tenant_id=body.target_tenant_id,
        prefix=body.prefix,
        is_active=True,
        created_by_user_id=user.id,
    )
    db.add(route)
    await db.commit()
    await db.refresh(route)

    logger.info(
        "inter_tenant_route_created",
        route_id=str(route.id),
        source=str(body.source_tenant_id),
        target=str(body.target_tenant_id),
        prefix=body.prefix,
    )
    return InterTenantRouteResponse.model_validate(route)


@router.delete("/{route_id}", response_model=InterTenantRouteResponse)
async def delete_inter_tenant_route(
    route_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Delete an inter-tenant route."""
    result = await db.execute(
        select(InterTenantRoute).where(InterTenantRoute.id == route_id)
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inter-tenant route not found",
        )

    await db.delete(route)
    await db.commit()

    logger.info("inter_tenant_route_deleted", route_id=str(route_id))
    return InterTenantRouteResponse.model_validate(route)

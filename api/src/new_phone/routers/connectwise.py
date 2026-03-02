from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.connectwise import (
    CWBoardResponse,
    CWCompanyMappingCreate,
    CWCompanyMappingResponse,
    CWCompanySearchResponse,
    CWConfigCreate,
    CWConfigResponse,
    CWConfigUpdate,
    CWStatusResponse,
    CWTestResponse,
    CWTicketLogResponse,
    CWTicketLogStats,
    CWTypeResponse,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.connectwise_service import ConnectWiseService

logger = structlog.get_logger()

router = APIRouter(prefix="/connectwise", tags=["connectwise"])


def _get_redis():
    from new_phone.main import redis_client
    return redis_client


# -- Config CRUD -------------------------------------------------------------


@router.get("/config", response_model=CWConfigResponse)
async def get_cw_config(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get ConnectWise configuration for the current tenant."""
    service = ConnectWiseService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConnectWise not configured")
    return CWConfigResponse.model_validate(config)


@router.post("/config", response_model=CWConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_cw_config(
    body: CWConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Create ConnectWise configuration for the current tenant."""
    service = ConnectWiseService(db, redis=_get_redis())
    try:
        config = await service.create_config(user.tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    await log_audit(db, user, request, "create", "cw_config", config.id)
    return CWConfigResponse.model_validate(config)


@router.patch("/config", response_model=CWConfigResponse)
async def update_cw_config(
    body: CWConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Update ConnectWise configuration for the current tenant."""
    service = ConnectWiseService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConnectWise not configured")
    try:
        updated = await service.update_config(config.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "update", "cw_config", updated.id)
    return CWConfigResponse.model_validate(updated)


@router.delete("/config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cw_config(
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Delete ConnectWise configuration for the current tenant."""
    service = ConnectWiseService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConnectWise not configured")
    await service.delete_config(config.id)
    await log_audit(db, user, request, "delete", "cw_config", config.id)


@router.post("/config/test", response_model=CWTestResponse)
async def test_cw_config(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Test ConnectWise API connectivity."""
    service = ConnectWiseService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConnectWise not configured")
    result = await service.test_connection(config.id)
    return CWTestResponse(**result)


# -- Company Mappings ---------------------------------------------------------


@router.get("/company-mappings", response_model=list[CWCompanyMappingResponse])
async def list_company_mappings(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """List company mappings for the current tenant."""
    service = ConnectWiseService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConnectWise not configured")
    mappings = await service.list_company_mappings(config.id)
    return [CWCompanyMappingResponse.model_validate(m) for m in mappings]


@router.post("/company-mappings", response_model=CWCompanyMappingResponse, status_code=status.HTTP_201_CREATED)
async def add_company_mapping(
    body: CWCompanyMappingCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Add a company mapping."""
    service = ConnectWiseService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConnectWise not configured")
    try:
        mapping = await service.add_company_mapping(config.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    await log_audit(db, user, request, "create", "cw_company_mapping", mapping.id)
    return CWCompanyMappingResponse.model_validate(mapping)


@router.delete("/company-mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company_mapping(
    mapping_id: str,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Delete a company mapping."""
    import uuid as _uuid

    service = ConnectWiseService(db, redis=_get_redis())
    try:
        await service.remove_company_mapping(_uuid.UUID(mapping_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "delete", "cw_company_mapping")


# -- CW Company Search -------------------------------------------------------


@router.get("/companies/search", response_model=list[CWCompanySearchResponse])
async def search_cw_companies(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    q: str = Query(..., min_length=1, max_length=100),
):
    """Search ConnectWise companies by name (proxy to CW API)."""
    service = ConnectWiseService(db, redis=_get_redis())
    results = await service.search_cw_companies(user.tenant_id, q)
    return [CWCompanySearchResponse(id=r["id"], name=r["name"], identifier=r.get("identifier", "")) for r in results]


# -- Boards / Statuses / Types -----------------------------------------------


@router.get("/boards", response_model=list[CWBoardResponse])
async def list_boards(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """List ConnectWise service boards (proxy to CW API)."""
    service = ConnectWiseService(db, redis=_get_redis())
    results = await service.get_cw_boards(user.tenant_id)
    return [CWBoardResponse(id=r["id"], name=r["name"]) for r in results]


@router.get("/boards/{board_id}/statuses", response_model=list[CWStatusResponse])
async def list_board_statuses(
    board_id: int,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """List statuses for a ConnectWise service board."""
    service = ConnectWiseService(db, redis=_get_redis())
    results = await service.get_cw_board_statuses(user.tenant_id, board_id)
    return [CWStatusResponse(id=r["id"], name=r["name"]) for r in results]


@router.get("/boards/{board_id}/types", response_model=list[CWTypeResponse])
async def list_board_types(
    board_id: int,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """List types for a ConnectWise service board."""
    service = ConnectWiseService(db, redis=_get_redis())
    results = await service.get_cw_board_types(user.tenant_id, board_id)
    return [CWTypeResponse(id=r["id"], name=r["name"]) for r in results]


# -- Ticket Logs --------------------------------------------------------------


@router.get("/ticket-logs", response_model=list[CWTicketLogResponse])
async def list_ticket_logs(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List ticket creation logs for the current tenant."""
    service = ConnectWiseService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConnectWise not configured")
    logs = await service.get_ticket_logs(config.id, limit=limit, offset=offset)
    return [CWTicketLogResponse.model_validate(log) for log in logs]


@router.get("/ticket-logs/stats", response_model=CWTicketLogStats)
async def get_ticket_log_stats(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get ticket creation statistics."""
    service = ConnectWiseService(db, redis=_get_redis())
    config = await service.get_config(user.tenant_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConnectWise not configured")
    stats = await service.get_ticket_log_stats(config.id)
    return CWTicketLogStats(**stats)

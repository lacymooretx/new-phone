import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.caller_id_rule import (
    CallerIdRuleCreate,
    CallerIdRuleResponse,
    CallerIdRuleUpdate,
)
from new_phone.services.caller_id_rule_service import CallerIdRuleService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/caller-id-rules", tags=["caller-id-rules"])


async def _sync_dialplan() -> None:
    try:
        from new_phone.main import config_sync
        if config_sync:
            await config_sync.notify_dialplan_change()
    except Exception as e:
        logger.warning("config_sync_failed", error=str(e))


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[CallerIdRuleResponse])
async def list_caller_id_rules(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_INBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = CallerIdRuleService(db)
    return await service.list_rules(tenant_id)


@router.post("", response_model=CallerIdRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_caller_id_rule(
    tenant_id: uuid.UUID,
    body: CallerIdRuleCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_INBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = CallerIdRuleService(db)
    try:
        rule = await service.create_rule(tenant_id, body)
        await _sync_dialplan()
        return rule
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{rule_id}", response_model=CallerIdRuleResponse)
async def get_caller_id_rule(
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_INBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = CallerIdRuleService(db)
    rule = await service.get_rule(tenant_id, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caller ID rule not found")
    return rule


@router.patch("/{rule_id}", response_model=CallerIdRuleResponse)
async def update_caller_id_rule(
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: CallerIdRuleUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_INBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = CallerIdRuleService(db)
    try:
        rule = await service.update_rule(tenant_id, rule_id, body)
        await _sync_dialplan()
        return rule
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{rule_id}", response_model=CallerIdRuleResponse)
async def deactivate_caller_id_rule(
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_INBOUND_ROUTES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = CallerIdRuleService(db)
    try:
        rule = await service.deactivate(tenant_id, rule_id)
        await _sync_dialplan()
        return rule
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None

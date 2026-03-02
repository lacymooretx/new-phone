import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.audit_log import AuditLogListParams, AuditLogResponse
from new_phone.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=dict)
async def list_audit_logs(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_AUDIT_LOGS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    tenant_id: Annotated[uuid.UUID | None, Query()] = None,
    user_id: Annotated[uuid.UUID | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    resource_type: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
):
    """List audit logs with filtering and pagination.

    MSP roles see all logs. TENANT_ADMIN sees only their tenant's logs.
    """
    params = AuditLogListParams(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
    )

    # Tenant-scoped users can only see their own tenant's logs
    if not is_msp_role(user.role):
        params.tenant_id = user.tenant_id

    service = AuditService(db)
    entries, total = await service.list_entries(params)

    return {
        "items": [AuditLogResponse.model_validate(e) for e in entries],
        "total": total,
        "page": params.page,
        "per_page": params.per_page,
    }

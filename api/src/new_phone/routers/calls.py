import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.extension import Extension
from new_phone.models.user import User
from new_phone.schemas.calls import (
    NumberHistoryEntry,
    OriginateRequest,
    OriginateResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/calls", tags=["calls"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post("/originate", response_model=OriginateResponse)
async def originate_call(
    tenant_id: uuid.UUID,
    body: OriginateRequest,
    user: Annotated[User, Depends(require_permission(Permission.PLACE_CALLS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Originate a call: ring the user's device, then bridge to destination."""
    _check_tenant_access(user, tenant_id)

    # Resolve caller extension
    if body.caller_extension_id:
        result = await db.execute(
            select(Extension).where(
                Extension.id == body.caller_extension_id,
                Extension.tenant_id == tenant_id,
                Extension.is_active.is_(True),
            )
        )
        ext = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(Extension).where(
                Extension.user_id == user.id,
                Extension.tenant_id == tenant_id,
                Extension.is_active.is_(True),
            )
        )
        ext = result.scalar_one_or_none()

    if not ext:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No extension found for this user",
        )

    from new_phone.main import freeswitch_service

    if not freeswitch_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FreeSWITCH service unavailable",
        )

    job_uuid = await freeswitch_service.originate_call(
        ext.sip_username, body.destination, body.originate_timeout
    )

    logger.info(
        "call_originated",
        tenant_id=str(tenant_id),
        user_id=str(user.id),
        extension=ext.extension_number,
        destination=body.destination,
        job_uuid=job_uuid,
    )

    return OriginateResponse(
        status="originating",
        destination=body.destination,
        caller_extension=ext.extension_number,
    )


@router.get("/history", response_model=list[NumberHistoryEntry])
async def get_call_history(
    tenant_id: uuid.UUID,
    number: str,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    limit: int = 10,
):
    """Get recent call history for a phone number."""
    _check_tenant_access(user, tenant_id)

    if limit > 50:
        limit = 50

    result = await db.execute(
        select(CallDetailRecord)
        .where(
            CallDetailRecord.tenant_id == tenant_id,
            or_(
                CallDetailRecord.caller_number == number,
                CallDetailRecord.called_number == number,
            ),
        )
        .order_by(CallDetailRecord.start_time.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

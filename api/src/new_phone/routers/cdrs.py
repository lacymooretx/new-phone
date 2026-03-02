import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.cdr import CDRDispositionUpdate, CDRFilter, CDRResponse
from new_phone.services.cdr_service import CDRService

router = APIRouter(prefix="/tenants/{tenant_id}/cdrs", tags=["cdrs"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[CDRResponse])
async def list_cdrs(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    extension_id: uuid.UUID | None = None,
    direction: str | None = None,
    disposition: str | None = None,
    site_id: uuid.UUID | None = None,
    crm_customer_name: str | None = None,
    crm_company_name: str | None = None,
    crm_account_number: str | None = None,
    crm_matched: bool | None = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    _check_tenant_access(user, tenant_id)
    filters = CDRFilter(
        date_from=date_from,
        date_to=date_to,
        extension_id=extension_id,
        direction=direction,
        disposition=disposition,
        site_id=site_id,
        crm_customer_name=crm_customer_name,
        crm_company_name=crm_company_name,
        crm_account_number=crm_account_number,
        crm_matched=crm_matched,
        limit=limit,
        offset=offset,
    )
    service = CDRService(db)
    return await service.list_cdrs(tenant_id, filters)


@router.get("/export")
async def export_cdrs(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    extension_id: uuid.UUID | None = None,
    direction: str | None = None,
    disposition: str | None = None,
    site_id: uuid.UUID | None = None,
):
    _check_tenant_access(user, tenant_id)
    filters = CDRFilter(
        date_from=date_from,
        date_to=date_to,
        extension_id=extension_id,
        direction=direction,
        disposition=disposition,
        site_id=site_id,
    )
    service = CDRService(db)
    csv_data = await service.export_csv(tenant_id, filters)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cdrs.csv"},
    )


@router.get("/{cdr_id}", response_model=CDRResponse)
async def get_cdr(
    tenant_id: uuid.UUID,
    cdr_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = CDRService(db)
    cdr = await service.get_cdr(tenant_id, cdr_id)
    if not cdr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CDR not found")
    return cdr


@router.patch("/{cdr_id}/disposition", response_model=CDRResponse)
async def set_cdr_disposition(
    tenant_id: uuid.UUID,
    cdr_id: uuid.UUID,
    body: CDRDispositionUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = CDRService(db)
    try:
        return await service.set_disposition(
            tenant_id, cdr_id, body.disposition_code_id, body.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None

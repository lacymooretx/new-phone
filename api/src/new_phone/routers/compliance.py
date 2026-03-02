import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.dnc import (
    BulkUploadResult,
    ComplianceAuditLogResponse,
    ComplianceSettingsResponse,
    ComplianceSettingsUpdate,
    ConsentRecordCreate,
    ConsentRecordResponse,
    DNCCheckRequest,
    DNCCheckResult,
    DNCEntryBulkCreate,
    DNCEntryCreate,
    DNCEntryResponse,
    DNCListCreate,
    DNCListResponse,
    DNCListUpdate,
    PaginatedResponse,
)
from new_phone.services.dnc_service import DNCService

router = APIRouter(
    prefix="/tenants/{tenant_id}/compliance",
    tags=["compliance"],
)


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ── DNC Lists ──


@router.get("/dnc-lists", response_model=list[DNCListResponse])
async def list_dnc_lists(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    lists = await service.list_dnc_lists(tenant_id)
    # Attach entry counts
    result = []
    for dnc_list in lists:
        count = await service._entry_count(dnc_list.id)
        resp = DNCListResponse.model_validate(dnc_list)
        resp.entry_count = count
        result.append(resp)
    return result


@router.post("/dnc-lists", response_model=DNCListResponse, status_code=status.HTTP_201_CREATED)
async def create_dnc_list(
    tenant_id: uuid.UUID,
    body: DNCListCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    dnc_list = await service.create_dnc_list(tenant_id, body)
    resp = DNCListResponse.model_validate(dnc_list)
    resp.entry_count = 0
    return resp


@router.get("/dnc-lists/{list_id}", response_model=DNCListResponse)
async def get_dnc_list(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    dnc_list, count = await service.get_dnc_list_with_count(tenant_id, list_id)
    if not dnc_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DNC list not found")
    resp = DNCListResponse.model_validate(dnc_list)
    resp.entry_count = count
    return resp


@router.patch("/dnc-lists/{list_id}", response_model=DNCListResponse)
async def update_dnc_list(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    body: DNCListUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    try:
        dnc_list = await service.update_dnc_list(tenant_id, list_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    count = await service._entry_count(list_id)
    resp = DNCListResponse.model_validate(dnc_list)
    resp.entry_count = count
    return resp


@router.delete("/dnc-lists/{list_id}", response_model=DNCListResponse)
async def delete_dnc_list(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    try:
        dnc_list = await service.delete_dnc_list(tenant_id, list_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    resp = DNCListResponse.model_validate(dnc_list)
    resp.entry_count = 0
    return resp


# ── DNC Entries ──


@router.get("/dnc-lists/{list_id}/entries", response_model=PaginatedResponse[DNCEntryResponse])
async def list_entries(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    items, total = await service.list_entries(tenant_id, list_id, page, per_page)
    return PaginatedResponse(
        items=[DNCEntryResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/dnc-lists/{list_id}/entries",
    response_model=DNCEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_entry(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    body: DNCEntryCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    # Verify list exists
    dnc_list = await service.get_dnc_list(tenant_id, list_id)
    if not dnc_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DNC list not found")
    try:
        entry = await service.add_entry(tenant_id, list_id, body, user.id)
    except Exception as e:
        if "uq_dnc_entries_list_phone" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already exists in this list",
            ) from None
        raise
    return entry


@router.post("/dnc-lists/{list_id}/entries/bulk", response_model=BulkUploadResult)
async def bulk_add_entries(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    body: DNCEntryBulkCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    dnc_list = await service.get_dnc_list(tenant_id, list_id)
    if not dnc_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DNC list not found")
    return await service.bulk_add_entries(
        tenant_id, list_id, body.phone_numbers, user.id, body.reason, body.source
    )


@router.delete("/dnc-lists/{list_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_entry(
    tenant_id: uuid.UUID,
    list_id: uuid.UUID,
    entry_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    try:
        await service.remove_entry(tenant_id, list_id, entry_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ── DNC Check ──


@router.post("/dnc-check", response_model=DNCCheckResult)
async def check_number(
    tenant_id: uuid.UUID,
    body: DNCCheckRequest,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    return await service.check_number(tenant_id, body.phone_number, user.id)


# ── Consent Records ──


@router.get("/consent-records", response_model=PaginatedResponse[ConsentRecordResponse])
async def list_consent_records(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    phone_number: str | None = None,
    campaign_type: str | None = None,
    is_active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    items, total = await service.list_consent_records(
        tenant_id, phone_number, campaign_type, is_active, page, per_page
    )
    return PaginatedResponse(
        items=[ConsentRecordResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/consent-records",
    response_model=ConsentRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_consent_record(
    tenant_id: uuid.UUID,
    body: ConsentRecordCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    return await service.create_consent_record(tenant_id, body, user.id)


@router.post("/consent-records/{record_id}/revoke", response_model=ConsentRecordResponse)
async def revoke_consent(
    tenant_id: uuid.UUID,
    record_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    try:
        return await service.revoke_consent(tenant_id, record_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


# ── Compliance Settings ──


@router.get("/settings", response_model=ComplianceSettingsResponse)
async def get_settings(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    return await service.get_settings(tenant_id)


@router.put("/settings", response_model=ComplianceSettingsResponse)
async def update_settings(
    tenant_id: uuid.UUID,
    body: ComplianceSettingsUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    return await service.update_settings(tenant_id, body, user.id)


# ── Audit Log ──


@router.get("/audit-log", response_model=PaginatedResponse[ComplianceAuditLogResponse])
async def list_audit_log(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    event_type: str | None = None,
    phone_number: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    items, total = await service.list_audit_log(
        tenant_id, event_type, phone_number, start_date, end_date, page, per_page
    )
    return PaginatedResponse(
        items=[ComplianceAuditLogResponse.model_validate(log) for log in items],
        total=total,
        page=page,
        per_page=per_page,
    )


# ── SMS Opt-Out Sync ──


@router.post("/sync-sms-optouts", response_model=BulkUploadResult)
async def sync_sms_optouts(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = DNCService(db)
    return await service.sync_sms_optouts_to_dnc(tenant_id, user.id)

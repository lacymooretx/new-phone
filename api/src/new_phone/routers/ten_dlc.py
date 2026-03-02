import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.ten_dlc import (
    BrandCreate,
    BrandResponse,
    BrandUpdate,
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    ComplianceDocUploadResponse,
    DocumentType,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.ten_dlc_service import TenDLCService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/10dlc", tags=["10dlc"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ── Brands ──────────────────────────────────────────────────────────────


@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    tenant_id: uuid.UUID,
    body: BrandCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    brand = await service.create_brand(tenant_id, body)
    return brand


@router.get("/brands", response_model=list[BrandResponse])
async def list_brands(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    return await service.list_brands(tenant_id)


@router.get("/brands/{brand_id}", response_model=BrandResponse)
async def get_brand(
    tenant_id: uuid.UUID,
    brand_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    brand = await service.get_brand(tenant_id, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return brand


@router.patch("/brands/{brand_id}", response_model=BrandResponse)
async def update_brand(
    tenant_id: uuid.UUID,
    brand_id: uuid.UUID,
    body: BrandUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    try:
        brand = await service.update_brand(tenant_id, brand_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    return brand


@router.post("/brands/{brand_id}/register", response_model=BrandResponse)
async def register_brand(
    tenant_id: uuid.UUID,
    brand_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    try:
        brand = await service.register_brand(tenant_id, brand_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    return brand


@router.get("/brands/{brand_id}/status", response_model=BrandResponse)
async def check_brand_status(
    tenant_id: uuid.UUID,
    brand_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    try:
        brand = await service.check_brand_status(tenant_id, brand_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    return brand


# ── Campaigns ───────────────────────────────────────────────────────────


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    tenant_id: uuid.UUID,
    body: CampaignCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    try:
        campaign = await service.create_campaign(tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    return campaign


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    brand_id: uuid.UUID | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    return await service.list_campaigns(tenant_id, brand_id=brand_id)


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    tenant_id: uuid.UUID,
    campaign_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    campaign = await service.get_campaign(tenant_id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


@router.patch("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    tenant_id: uuid.UUID,
    campaign_id: uuid.UUID,
    body: CampaignUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    try:
        campaign = await service.update_campaign(tenant_id, campaign_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    return campaign


@router.post("/campaigns/{campaign_id}/register", response_model=CampaignResponse)
async def register_campaign(
    tenant_id: uuid.UUID,
    campaign_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    try:
        campaign = await service.register_campaign(tenant_id, campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None
    return campaign


@router.get("/campaigns/{campaign_id}/status", response_model=CampaignResponse)
async def check_campaign_status(
    tenant_id: uuid.UUID,
    campaign_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    try:
        campaign = await service.check_campaign_status(tenant_id, campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    return campaign


# ── Compliance Documents ────────────────────────────────────────────────


@router.post(
    "/compliance-docs",
    response_model=ComplianceDocUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_compliance_doc(
    tenant_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    brand_id: uuid.UUID = Form(...),
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
):
    _check_tenant_access(user, tenant_id)

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is required")

    # Upload to MinIO
    from new_phone.main import storage_service

    if not storage_service or not storage_service.client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service unavailable",
        )

    object_name = f"tenants/{tenant_id}/10dlc/{brand_id}/{document_type}/{file.filename}"
    file_data = await file.read()
    content_type = file.content_type or "application/octet-stream"

    uploaded = storage_service.upload_bytes(object_name, file_data, content_type=content_type)
    if not uploaded:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document to storage",
        )

    service = TenDLCService(db)
    try:
        doc = await service.upload_compliance_doc(
            tenant_id=tenant_id,
            brand_id=brand_id,
            document_type=document_type,
            file_path=object_name,
            original_filename=file.filename,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None

    await log_audit(
        db, user, request, "upload_compliance_doc", "ten_dlc_compliance_doc",
        resource_id=doc.id,
        changes={"document_type": document_type, "filename": file.filename},
    )

    return doc


@router.get("/compliance-docs", response_model=list[ComplianceDocUploadResponse])
async def list_compliance_docs(
    tenant_id: uuid.UUID,
    brand_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = TenDLCService(db)
    return await service.list_compliance_docs(tenant_id, brand_id)

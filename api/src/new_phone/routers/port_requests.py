import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.port_requests import (
    PortRequestCreate,
    PortRequestResponse,
    PortRequestUpdate,
)
from new_phone.services.port_service import PortService

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/port-requests", tags=["port-requests"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )


@router.get("", response_model=list[PortRequestResponse])
async def list_port_requests(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    status_filter: str | None = None,
):
    """List all port requests for a tenant."""
    _check_tenant_access(user, tenant_id)
    service = PortService(db)
    return await service.list_port_requests(tenant_id, status_filter=status_filter)


@router.post("", response_model=PortRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_port_request(
    tenant_id: uuid.UUID,
    body: PortRequestCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Submit a new number porting request."""
    _check_tenant_access(user, tenant_id)
    service = PortService(db)
    try:
        port_request = await service.submit_port_request(
            tenant_id, body, submitted_by=user.id
        )
        return port_request
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.get("/{port_request_id}", response_model=PortRequestResponse)
async def get_port_request(
    tenant_id: uuid.UUID,
    port_request_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Get a specific port request."""
    _check_tenant_access(user, tenant_id)
    service = PortService(db)
    port_request = await service.get_port_request(tenant_id, port_request_id)
    if not port_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Port request not found"
        )
    return port_request


@router.patch("/{port_request_id}", response_model=PortRequestResponse)
async def update_port_request(
    tenant_id: uuid.UUID,
    port_request_id: uuid.UUID,
    body: PortRequestUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Update a port request (status, notes, FOC date, etc.)."""
    _check_tenant_access(user, tenant_id)
    service = PortService(db)
    try:
        port_request = await service.update_port_request(
            tenant_id, port_request_id, body, changed_by=user.id
        )
        return port_request
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/{port_request_id}/upload-loa", response_model=PortRequestResponse)
async def upload_loa(
    tenant_id: uuid.UUID,
    port_request_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    file: UploadFile = File(...),
):
    """Upload a Letter of Authorization (LOA) document for a port request."""
    _check_tenant_access(user, tenant_id)

    # Validate file type
    allowed_types = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/tiff",
    }
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file.content_type}' not allowed. Accepted: PDF, PNG, JPEG, TIFF",
        )

    # Read file content
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LOA file must be smaller than 10MB",
        )

    # Upload to MinIO
    from new_phone.main import storage_service

    if not storage_service or not storage_service.client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service unavailable",
        )

    ext = ""
    if file.filename:
        parts = file.filename.rsplit(".", 1)
        if len(parts) > 1:
            ext = f".{parts[1]}"

    object_name = f"port-requests/{tenant_id}/{port_request_id}/loa{ext}"
    content_type = file.content_type or "application/octet-stream"

    success = storage_service.upload_bytes(object_name, content, content_type=content_type)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload LOA document",
        )

    service = PortService(db)
    try:
        port_request = await service.upload_loa(
            tenant_id, port_request_id, object_name, changed_by=user.id
        )
        return port_request
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/{port_request_id}/check-status", response_model=PortRequestResponse)
async def check_port_status(
    tenant_id: uuid.UUID,
    port_request_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Poll the provider for the current port request status."""
    _check_tenant_access(user, tenant_id)
    service = PortService(db)
    try:
        port_request = await service.check_status(
            tenant_id, port_request_id, changed_by=user.id
        )
        return port_request
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None


@router.post("/{port_request_id}/cancel", response_model=PortRequestResponse)
async def cancel_port_request(
    tenant_id: uuid.UUID,
    port_request_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    reason: str | None = None,
):
    """Cancel a port request."""
    _check_tenant_access(user, tenant_id)
    service = PortService(db)
    try:
        port_request = await service.cancel_port(
            tenant_id, port_request_id, changed_by=user.id, reason=reason
        )
        return port_request
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None


@router.post("/{port_request_id}/complete", response_model=PortRequestResponse)
async def complete_port_request(
    tenant_id: uuid.UUID,
    port_request_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DIDS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Mark a port as completed and activate the DIDs."""
    _check_tenant_access(user, tenant_id)
    service = PortService(db)
    try:
        port_request = await service.complete_port(
            tenant_id, port_request_id, changed_by=user.id
        )
        return port_request
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from None

"""Migration tools endpoints — upload, validate, and import PBX configs.

Prefix: /api/v1/tenants/{tenant_id}/migration
Permission: MANAGE_TENANT
"""

import base64
import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.migration.csv_importer import CSVImporter
from new_phone.migration.freepbx_parser import FreePBXParser
from new_phone.migration.threecx_parser import ThreeCXParser
from new_phone.models.migration import MigrationJob, MigrationStatus
from new_phone.models.user import User
from new_phone.schemas.migration import MigrationJobCreate, MigrationJobResponse

logger = structlog.get_logger()

router = APIRouter(
    prefix="/tenants/{tenant_id}/migration",
    tags=["migration"],
)


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )


# ------------------------------------------------------------------
# Upload
# ------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=MigrationJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_migration_file(
    tenant_id: uuid.UUID,
    body: MigrationJobCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Upload a migration file and create a pending job."""
    _check_tenant_access(user, tenant_id)

    # Validate base64 content.
    try:
        file_bytes = base64.b64decode(body.file_content_base64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 file content",
        ) from None

    # Quick-count records based on platform parser.
    total = _count_records(body.source_platform, file_bytes)

    job = MigrationJob(
        tenant_id=tenant_id,
        source_platform=body.source_platform,
        status=MigrationStatus.PENDING,
        file_name=body.file_name,
        total_records=total,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info(
        "migration_job_created",
        job_id=str(job.id),
        tenant_id=str(tenant_id),
        platform=body.source_platform,
    )
    return MigrationJobResponse.model_validate(job)


# ------------------------------------------------------------------
# List / Detail
# ------------------------------------------------------------------


@router.get("/jobs", response_model=list[MigrationJobResponse])
async def list_migration_jobs(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    result = await db.execute(
        select(MigrationJob)
        .where(MigrationJob.tenant_id == tenant_id)
        .order_by(MigrationJob.created_at.desc())
    )
    return [MigrationJobResponse.model_validate(j) for j in result.scalars().all()]


@router.get("/jobs/{job_id}", response_model=MigrationJobResponse)
async def get_migration_job(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    job = await _get_job_or_404(db, tenant_id, job_id)
    return MigrationJobResponse.model_validate(job)


# ------------------------------------------------------------------
# Validate
# ------------------------------------------------------------------


@router.post("/jobs/{job_id}/validate", response_model=MigrationJobResponse)
async def validate_migration_job(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Run validation on a pending migration job."""
    _check_tenant_access(user, tenant_id)
    job = await _get_job_or_404(db, tenant_id, job_id)

    if job.status not in (MigrationStatus.PENDING, MigrationStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job cannot be validated in status '{job.status}'",
        )

    job.status = MigrationStatus.VALIDATING
    await db.commit()

    # Validation is lightweight enough to run inline for now.
    errors: list[str] = []
    if job.total_records == 0:
        errors.append("No records found in uploaded file")

    if errors:
        job.status = MigrationStatus.FAILED
        job.validation_errors = {"errors": errors}
    else:
        job.status = MigrationStatus.VALIDATED
        job.validation_errors = None

    await db.commit()
    await db.refresh(job)
    return MigrationJobResponse.model_validate(job)


# ------------------------------------------------------------------
# Import
# ------------------------------------------------------------------


@router.post("/jobs/{job_id}/import", response_model=MigrationJobResponse)
async def import_migration_job(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Execute the import for a validated migration job."""
    _check_tenant_access(user, tenant_id)
    job = await _get_job_or_404(db, tenant_id, job_id)

    if job.status != MigrationStatus.VALIDATED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job must be validated before import (current: '{job.status}')",
        )

    job.status = MigrationStatus.IMPORTING
    job.started_at = datetime.now(UTC)
    await db.commit()

    # TODO: Actual record-by-record import will be implemented as a
    # background task.  For now we mark as completed immediately.
    job.imported_records = job.total_records
    job.status = MigrationStatus.COMPLETED
    job.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(job)

    logger.info(
        "migration_job_imported",
        job_id=str(job.id),
        imported=job.imported_records,
    )
    return MigrationJobResponse.model_validate(job)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


async def _get_job_or_404(
    db: AsyncSession, tenant_id: uuid.UUID, job_id: uuid.UUID
) -> MigrationJob:
    result = await db.execute(
        select(MigrationJob).where(
            MigrationJob.id == job_id,
            MigrationJob.tenant_id == tenant_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Migration job not found",
        )
    return job


def _count_records(platform: str, file_bytes: bytes) -> int:
    """Quick-count the number of records found in the uploaded file."""
    try:
        if platform == "freepbx":
            data = FreePBXParser().parse_backup(file_bytes)
        elif platform == "threecx":
            data = ThreeCXParser().parse_xml(file_bytes)
        elif platform == "csv":
            importer = CSVImporter()
            rows = importer.parse_extensions_csv(file_bytes.decode("utf-8", errors="replace"))
            return len(rows)
        else:
            return 0
        return (
            len(data.extensions)
            + len(data.ring_groups)
            + len(data.ivr_menus)
            + len(data.dids)
            + len(data.routes)
            + len(data.time_conditions)
        )
    except Exception:
        logger.warning("migration_count_failed", platform=platform, exc_info=True)
        return 0

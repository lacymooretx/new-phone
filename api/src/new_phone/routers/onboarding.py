"""Tenant onboarding router — full lifecycle orchestration."""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.did import DID
from new_phone.models.extension import Extension
from new_phone.models.sip_trunk import SIPTrunk
from new_phone.models.tenant import Tenant
from new_phone.models.user import User
from new_phone.schemas.onboarding import (
    OnboardingRequest,
    OnboardingResponse,
    OnboardingStatusResponse,
    OnboardingStepStatus,
)
from new_phone.services.tenant_service import TenantService

logger = structlog.get_logger()

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/tenant", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
async def onboard_tenant(
    body: OnboardingRequest,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_PLATFORM))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Kick off full tenant onboarding: create tenant, provision trunk,
    purchase DIDs, create admin user, and create default extensions."""
    if not is_msp_role(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only MSP roles can onboard new tenants",
        )

    service = TenantService(db)
    try:
        result = await service.onboard_tenant(
            name=body.name,
            slug=body.slug,
            domain=body.domain,
            admin_email=body.admin_email,
            admin_first_name=body.admin_first_name,
            admin_last_name=body.admin_last_name,
            plan=body.plan,
            provider=body.provider,
            region=body.region,
            area_code=body.area_code,
            initial_did_count=body.initial_did_count,
            initial_extensions=body.initial_extensions,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from None
    except Exception as exc:
        logger.error("onboarding_failed", error=str(exc), slug=body.slug)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Onboarding failed: {exc}",
        ) from None

    tenant: Tenant = result["tenant"]
    return OnboardingResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        slug=tenant.slug,
        lifecycle_state=tenant.lifecycle_state,
        admin_email=body.admin_email,
        trunk_provisioned=result["trunk_provisioned"],
        dids_purchased=result["dids_purchased"],
        extensions_created=result["extensions_created"],
        message="Tenant onboarded successfully",
    )


@router.get("/status/{tenant_id}", response_model=OnboardingStatusResponse)
async def onboarding_status(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_ALL_TENANTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Return the current onboarding state of a tenant by inspecting
    the resources that should have been created during onboarding."""
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    steps: list[OnboardingStepStatus] = []

    # Step 1: Tenant exists (always true at this point)
    steps.append(OnboardingStepStatus(step="create_tenant", status="completed"))

    # Step 2: Trunk provisioned?
    trunk_result = await db.execute(
        select(SIPTrunk).where(
            SIPTrunk.tenant_id == tenant_id,
            SIPTrunk.is_active.is_(True),
        ).limit(1)
    )
    trunk = trunk_result.scalar_one_or_none()
    if trunk:
        steps.append(OnboardingStepStatus(
            step="provision_trunk",
            status="completed",
            detail=f"Trunk: {trunk.name}",
        ))
    else:
        steps.append(OnboardingStepStatus(step="provision_trunk", status="pending"))

    # Step 3: DIDs purchased?
    did_result = await db.execute(
        select(DID).where(
            DID.tenant_id == tenant_id,
            DID.is_active.is_(True),
        )
    )
    dids = list(did_result.scalars().all())
    if dids:
        steps.append(OnboardingStepStatus(
            step="purchase_dids",
            status="completed",
            detail=f"{len(dids)} DID(s) active",
        ))
    else:
        steps.append(OnboardingStepStatus(step="purchase_dids", status="pending"))

    # Step 4: Admin user?
    admin_result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.role == "tenant_admin",
            User.is_active.is_(True),
        ).limit(1)
    )
    admin_user = admin_result.scalar_one_or_none()
    if admin_user:
        steps.append(OnboardingStepStatus(
            step="create_admin",
            status="completed",
            detail=admin_user.email,
        ))
    else:
        steps.append(OnboardingStepStatus(step="create_admin", status="pending"))

    # Step 5: Extensions created?
    ext_result = await db.execute(
        select(Extension).where(
            Extension.tenant_id == tenant_id,
            Extension.is_active.is_(True),
        )
    )
    extensions = list(ext_result.scalars().all())
    if extensions:
        steps.append(OnboardingStepStatus(
            step="create_extensions",
            status="completed",
            detail=f"{len(extensions)} extension(s)",
        ))
    else:
        steps.append(OnboardingStepStatus(step="create_extensions", status="pending"))

    all_completed = all(s.status == "completed" for s in steps)

    return OnboardingStatusResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        lifecycle_state=tenant.lifecycle_state,
        steps=steps,
        completed=all_completed,
        created_at=tenant.created_at,
    )

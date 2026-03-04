import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_db_with_tenant, require_permission
from new_phone.models.user import User
from new_phone.schemas.survey import (
    SurveyResponseCreate,
    SurveyResponseResponse,
    SurveyTemplateCreate,
    SurveyTemplateResponse,
    SurveyTemplateUpdate,
)
from new_phone.services.survey_service import SurveyService

router = APIRouter(prefix="/tenants/{tenant_id}/surveys", tags=["surveys"])


# ── Templates ──────────────────────────────────────────────
@router.get("/templates", response_model=list[SurveyTemplateResponse])
async def list_templates(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
):
    service = SurveyService(db)
    return await service.list_templates(tenant_id)


@router.post("/templates", response_model=SurveyTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    tenant_id: uuid.UUID,
    data: SurveyTemplateCreate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
):
    service = SurveyService(db)
    return await service.create_template(tenant_id, **data.model_dump())


@router.get("/templates/{template_id}", response_model=SurveyTemplateResponse)
async def get_template(
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
):
    service = SurveyService(db)
    tmpl = await service.get_template(tenant_id, template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Survey template not found")
    return tmpl


@router.put("/templates/{template_id}", response_model=SurveyTemplateResponse)
async def update_template(
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    data: SurveyTemplateUpdate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
):
    service = SurveyService(db)
    tmpl = await service.update_template(tenant_id, template_id, **data.model_dump(exclude_unset=True))
    if not tmpl:
        raise HTTPException(status_code=404, detail="Survey template not found")
    return tmpl


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
):
    service = SurveyService(db)
    deleted = await service.delete_template(tenant_id, template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Survey template not found")


# ── Responses ──────────────────────────────────────────────
@router.get("/responses", response_model=dict)
async def list_responses(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
    template_id: Annotated[uuid.UUID | None, Query()] = None,
    queue_id: Annotated[uuid.UUID | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
):
    service = SurveyService(db)
    items, total = await service.list_responses(tenant_id, template_id, queue_id, page, per_page)
    return {
        "items": [SurveyResponseResponse.model_validate(r) for r in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/responses", response_model=SurveyResponseResponse, status_code=status.HTTP_201_CREATED)
async def create_response(
    tenant_id: uuid.UUID,
    data: SurveyResponseCreate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_QUEUES))],
):
    service = SurveyService(db)
    return await service.create_response(tenant_id, **data.model_dump())


# ── Analytics ──────────────────────────────────────────────
@router.get("/templates/{template_id}/analytics")
async def get_survey_analytics(
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.VIEW_QUEUES))],
):
    service = SurveyService(db)
    try:
        return await service.get_analytics(tenant_id, template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None

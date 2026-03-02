import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.phone_model import (
    PhoneModelCreate,
    PhoneModelResponse,
    PhoneModelUpdate,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.phone_model_service import PhoneModelService

logger = structlog.get_logger()

router = APIRouter(prefix="/phone-models", tags=["phone-models"])


@router.get("", response_model=list[PhoneModelResponse])
async def list_phone_models(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = PhoneModelService(db)
    return await service.list_phone_models()


@router.get("/{model_id}", response_model=PhoneModelResponse)
async def get_phone_model(
    model_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = PhoneModelService(db)
    model = await service.get_phone_model(model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone model not found")
    return model


@router.post("", response_model=PhoneModelResponse, status_code=status.HTTP_201_CREATED)
async def create_phone_model(
    body: PhoneModelCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = PhoneModelService(db)
    model = await service.create_phone_model(body)
    await log_audit(db, user, request, "create", "phone_model", model.id)
    return model


@router.patch("/{model_id}", response_model=PhoneModelResponse)
async def update_phone_model(
    model_id: uuid.UUID,
    body: PhoneModelUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = PhoneModelService(db)
    try:
        model = await service.update_phone_model(model_id, body)
        await log_audit(db, user, request, "update", "phone_model", model.id)
        return model
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.delete("/{model_id}", response_model=PhoneModelResponse)
async def delete_phone_model(
    model_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_DEVICES))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = PhoneModelService(db)
    try:
        model = await service.delete_phone_model(model_id)
        await log_audit(db, user, request, "delete", "phone_model", model.id)
        return model
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None

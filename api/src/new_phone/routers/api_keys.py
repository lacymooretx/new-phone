import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_db_with_tenant, require_permission
from new_phone.models.user import User
from new_phone.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ApiKeyUpdate,
)
from new_phone.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/tenants/{tenant_id}/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = ApiKeyService(db)
    return await service.list_keys(tenant_id)


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    tenant_id: uuid.UUID,
    data: ApiKeyCreate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = ApiKeyService(db)
    api_key, raw_key = await service.create_key(
        tenant_id, user.id,
        name=data.name,
        scopes=data.scopes,
        rate_limit=data.rate_limit,
        description=data.description,
        expires_at=data.expires_at,
    )
    response = ApiKeyCreatedResponse.model_validate(api_key)
    response.raw_key = raw_key
    return response


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    tenant_id: uuid.UUID,
    key_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = ApiKeyService(db)
    key = await service.get_key(tenant_id, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return key


@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    tenant_id: uuid.UUID,
    key_id: uuid.UUID,
    data: ApiKeyUpdate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = ApiKeyService(db)
    key = await service.update_key(tenant_id, key_id, **data.model_dump(exclude_unset=True))
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    tenant_id: uuid.UUID,
    key_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = ApiKeyService(db)
    deleted = await service.delete_key(tenant_id, key_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")

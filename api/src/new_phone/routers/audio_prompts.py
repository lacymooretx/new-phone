import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.audio_prompt import PromptCategory
from new_phone.models.tenant import Tenant
from new_phone.models.user import User
from new_phone.schemas.audio_prompt import (
    AudioPromptPlaybackResponse,
    AudioPromptResponse,
)
from new_phone.services.audio_prompt_service import AudioPromptService

router = APIRouter(prefix="/tenants/{tenant_id}/audio-prompts", tags=["audio-prompts"])


def _get_storage():
    from new_phone.main import storage_service
    return storage_service


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("", response_model=list[AudioPromptResponse])
async def list_prompts(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    category: str | None = None,
    site_id: uuid.UUID | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = AudioPromptService(db, _get_storage())
    return await service.list_prompts(tenant_id, category, site_id=site_id)


_file_field = File(...)
_category_field = Form(PromptCategory.GENERAL)


@router.post("", response_model=AudioPromptResponse, status_code=status.HTTP_201_CREATED)
async def upload_prompt(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    file: UploadFile = _file_field,
    name: str = Form(...),
    category: PromptCategory = _category_field,
    description: str | None = Form(None),
):
    _check_tenant_access(user, tenant_id)

    # Get tenant slug for storage paths
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    service = AudioPromptService(db, _get_storage())
    try:
        return await service.create_prompt(
            tenant_id=tenant_id,
            tenant_slug=tenant.slug,
            name=name,
            category=category,
            description=description,
            file_data=file_data,
            filename=file.filename or "prompt.wav",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/{prompt_id}", response_model=AudioPromptResponse)
async def get_prompt(
    tenant_id: uuid.UUID,
    prompt_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = AudioPromptService(db, _get_storage())
    prompt = await service.get_prompt(tenant_id, prompt_id)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio prompt not found")
    return prompt


@router.get("/{prompt_id}/playback", response_model=AudioPromptPlaybackResponse)
async def get_playback_url(
    tenant_id: uuid.UUID,
    prompt_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = AudioPromptService(db, _get_storage())
    url = await service.get_playback_url(tenant_id, prompt_id)
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found or no file")
    return AudioPromptPlaybackResponse(url=url)


@router.delete("/{prompt_id}", response_model=AudioPromptResponse)
async def delete_prompt(
    tenant_id: uuid.UUID,
    prompt_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_IVR))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = AudioPromptService(db, _get_storage())
    prompt = await service.soft_delete(tenant_id, prompt_id)
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio prompt not found")
    return prompt

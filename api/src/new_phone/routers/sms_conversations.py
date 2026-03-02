import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.sms import (
    ConversationNoteCreate,
    ConversationNoteResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from new_phone.services.audit_utils import log_audit
from new_phone.services.sms_service import SMSService


class ReassignBody(BaseModel):
    user_id: uuid.UUID

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/sms/conversations", tags=["sms-conversations"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _conversation_to_response(conv) -> ConversationResponse:
    return ConversationResponse(
        id=conv.id,
        tenant_id=conv.tenant_id,
        did_id=conv.did_id,
        remote_number=conv.remote_number,
        channel=conv.channel,
        state=conv.state,
        assigned_to_user_id=conv.assigned_to_user_id,
        queue_id=conv.queue_id,
        last_message_at=conv.last_message_at,
        first_response_at=conv.first_response_at,
        resolved_at=conv.resolved_at,
        is_active=conv.is_active,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        did_number=conv.did.number if conv.did else None,
        assigned_to_name=(
            f"{conv.assigned_to_user.first_name} {conv.assigned_to_user.last_name}"
            if conv.assigned_to_user
            else None
        ),
        queue_name=conv.queue.name if conv.queue else None,
        last_message_preview=(
            conv.messages[-1].body[:100] if hasattr(conv, "messages") and conv.messages else None
        ),
    )


def _message_to_response(msg) -> MessageResponse:
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        direction=msg.direction,
        from_number=msg.from_number,
        to_number=msg.to_number,
        body=msg.body,
        status=msg.status,
        provider=msg.provider,
        provider_message_id=msg.provider_message_id,
        sent_by_user_id=msg.sent_by_user_id,
        error_message=msg.error_message,
        segments=msg.segments,
        created_at=msg.created_at,
        sent_by_name=(
            f"{msg.sent_by_user.first_name} {msg.sent_by_user.last_name}"
            if msg.sent_by_user
            else None
        ),
    )


def _note_to_response(note) -> ConversationNoteResponse:
    return ConversationNoteResponse(
        id=note.id,
        conversation_id=note.conversation_id,
        user_id=note.user_id,
        body=note.body,
        created_at=note.created_at,
        user_name=(
            f"{note.user.first_name} {note.user.last_name}"
            if note.user
            else None
        ),
    )


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    state: str | None = Query(None, description="Filter by state: open, waiting, resolved, archived"),
    queue_id: uuid.UUID | None = Query(None, description="Filter by queue"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
):
    _check_tenant_access(user, tenant_id)
    service = SMSService(db)
    conversations, _total = await service.list_conversations(tenant_id, state, queue_id, page, per_page)
    return [_conversation_to_response(c) for c in conversations]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SMSService(db)
    conv = await service.get_conversation(tenant_id, conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return _conversation_to_response(conv)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: ConversationUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SMSService(db)
    # Only pass queue_id if it was explicitly in the request body
    fields = body.model_fields_set
    kwargs: dict = {}
    if body.state is not None:
        kwargs["state"] = body.state
    if body.assigned_to_user_id is not None:
        kwargs["assigned_to_user_id"] = body.assigned_to_user_id
    if "queue_id" in fields:
        kwargs["queue_id"] = body.queue_id
    try:
        conv = await service.update_conversation(tenant_id, conversation_id, **kwargs)
        await log_audit(db, user, request, "update", "sms_conversation", conv.id)
        return _conversation_to_response(conv)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    _check_tenant_access(user, tenant_id)
    service = SMSService(db)
    messages = await service.list_messages(tenant_id, conversation_id, limit, offset)
    return [_message_to_response(m) for m in messages]


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: MessageCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SMSService(db)
    try:
        msg = await service.send_message(tenant_id, conversation_id, body.body, user.id)
        await log_audit(db, user, request, "send", "sms_message", msg.id)
        return _message_to_response(msg)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.get("/{conversation_id}/notes", response_model=list[ConversationNoteResponse])
async def list_notes(
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SMSService(db)
    notes = await service.list_notes(tenant_id, conversation_id)
    return [_note_to_response(n) for n in notes]


@router.post("/{conversation_id}/notes", response_model=ConversationNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: ConversationNoteCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = SMSService(db)
    note = await service.create_note(tenant_id, conversation_id, user.id, body.body)
    await log_audit(db, user, request, "create", "sms_note", note.id)
    return _note_to_response(note)


# ── Assignment (Claim / Release / Reassign) ──────────────────────


@router.post("/{conversation_id}/claim", response_model=ConversationResponse)
async def claim_conversation(
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Current user claims an unassigned conversation."""
    _check_tenant_access(user, tenant_id)
    service = SMSService(db)
    try:
        conv = await service.claim_conversation(tenant_id, conversation_id, user.id)
        await log_audit(db, user, request, "claim", "sms_conversation", conv.id)
        return _conversation_to_response(conv)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.post("/{conversation_id}/release", response_model=ConversationResponse)
async def release_conversation(
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Release a conversation back to the shared inbox."""
    _check_tenant_access(user, tenant_id)
    service = SMSService(db)
    try:
        conv = await service.release_conversation(
            tenant_id, conversation_id, user.id, is_msp=is_msp_role(user.role)
        )
        await log_audit(db, user, request, "release", "sms_conversation", conv.id)
        return _conversation_to_response(conv)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.post("/{conversation_id}/reassign", response_model=ConversationResponse)
async def reassign_conversation(
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: ReassignBody,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_SMS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Supervisor reassigns a conversation to another user."""
    _check_tenant_access(user, tenant_id)
    service = SMSService(db)
    try:
        conv = await service.reassign_conversation(tenant_id, conversation_id, body.user_id)
        await log_audit(db, user, request, "reassign", "sms_conversation", conv.id)
        return _conversation_to_response(conv)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None

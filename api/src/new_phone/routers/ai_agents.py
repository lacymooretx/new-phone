"""AI Voice Agent REST endpoints."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.ai_agent import (
    AIAgentContextCreate,
    AIAgentContextResponse,
    AIAgentContextUpdate,
    AIAgentConversationDetail,
    AIAgentConversationResponse,
    AIAgentProviderStatus,
    AIAgentProviderTestResponse,
    AIAgentStatsResponse,
    AIAgentTestRequest,
    AIAgentTestResponse,
    AIAgentToolCreate,
    AIAgentToolResponse,
    AIAgentToolUpdate,
    AIProviderConfigCreate,
    AIProviderConfigResponse,
    AIProviderConfigUpdate,
    ESLHangupRequest,
    ESLHoldRequest,
    ESLTransferRequest,
)
from new_phone.services.ai_agent_service import AIAgentService
from new_phone.services.audit_utils import log_audit

logger = structlog.get_logger()

router = APIRouter(prefix="/ai-agents", tags=["ai-agents"])


# ── Provider Configs ─────────────────────────────────────────────

@router.get("/provider-configs", response_model=list[AIProviderConfigResponse])
async def list_provider_configs(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = AIAgentService(db)
    configs = await service.list_provider_configs(user.tenant_id)
    return [AIProviderConfigResponse.model_validate(c) for c in configs]


@router.post("/provider-configs", response_model=AIProviderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_provider_config(
    body: AIProviderConfigCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = AIAgentService(db)
    try:
        config = await service.create_provider_config(user.tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    await log_audit(db, user, request, "create", "ai_provider_config", config.id)
    return AIProviderConfigResponse.model_validate(config)


@router.patch("/provider-configs/{config_id}", response_model=AIProviderConfigResponse)
async def update_provider_config(
    config_id: str,
    body: AIProviderConfigUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid as _uuid
    service = AIAgentService(db)
    try:
        config = await service.update_provider_config(_uuid.UUID(config_id), body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "update", "ai_provider_config", config.id)
    return AIProviderConfigResponse.model_validate(config)


@router.delete("/provider-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_config(
    config_id: str,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid as _uuid
    service = AIAgentService(db)
    try:
        await service.delete_provider_config(_uuid.UUID(config_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "delete", "ai_provider_config")


@router.post("/provider-configs/{config_id}/test", response_model=AIAgentProviderTestResponse)
async def test_provider_config(
    config_id: str,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid as _uuid
    service = AIAgentService(db)
    try:
        result = await service.test_provider_config(_uuid.UUID(config_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    return AIAgentProviderTestResponse(**result)


# ── Agent Contexts ───────────────────────────────────────────────

@router.get("/contexts", response_model=list[AIAgentContextResponse])
async def list_contexts(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = AIAgentService(db)
    contexts = await service.list_contexts(user.tenant_id)
    return [AIAgentContextResponse.model_validate(c) for c in contexts]


@router.get("/contexts/{context_id}", response_model=AIAgentContextResponse)
async def get_context(
    context_id: str,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid as _uuid
    service = AIAgentService(db)
    context = await service.get_context(_uuid.UUID(context_id))
    if not context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI agent context not found")
    return AIAgentContextResponse.model_validate(context)


@router.post("/contexts", response_model=AIAgentContextResponse, status_code=status.HTTP_201_CREATED)
async def create_context(
    body: AIAgentContextCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = AIAgentService(db)
    try:
        context = await service.create_context(user.tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    await log_audit(db, user, request, "create", "ai_agent_context", context.id)
    return AIAgentContextResponse.model_validate(context)


@router.put("/contexts/{context_id}", response_model=AIAgentContextResponse)
async def update_context(
    context_id: str,
    body: AIAgentContextUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid as _uuid
    service = AIAgentService(db)
    try:
        context = await service.update_context(_uuid.UUID(context_id), body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "update", "ai_agent_context", context.id)
    return AIAgentContextResponse.model_validate(context)


@router.delete("/contexts/{context_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_context(
    context_id: str,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid as _uuid
    service = AIAgentService(db)
    try:
        await service.delete_context(_uuid.UUID(context_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "delete", "ai_agent_context")


@router.post("/contexts/{context_id}/test", response_model=AIAgentTestResponse)
async def test_context(
    context_id: str,
    body: AIAgentTestRequest,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Text-based test of an AI agent context."""
    import uuid as _uuid

    import httpx

    from new_phone.config import settings as app_settings

    service = AIAgentService(db)
    context = await service.get_context(_uuid.UUID(context_id))
    if not context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI agent context not found")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{app_settings.ai_engine_url}/test-context",
                json={
                    "tenant_id": str(user.tenant_id),
                    "context_id": str(context.id),
                    "message": body.message,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return AIAgentTestResponse(
                success=True,
                response=data.get("response", ""),
                provider=data.get("provider", ""),
                latency_ms=data.get("latency_ms", 0),
            )
    except Exception as e:
        return AIAgentTestResponse(success=False, response=str(e))


# ── Custom Tools ─────────────────────────────────────────────────

@router.get("/tools", response_model=list[AIAgentToolResponse])
async def list_tools(
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = AIAgentService(db)
    tools = await service.list_tools(user.tenant_id)
    return [AIAgentToolResponse.model_validate(t) for t in tools]


@router.post("/tools", response_model=AIAgentToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    body: AIAgentToolCreate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = AIAgentService(db)
    try:
        tool = await service.create_tool(user.tenant_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None
    await log_audit(db, user, request, "create", "ai_agent_tool", tool.id)
    return AIAgentToolResponse.model_validate(tool)


@router.patch("/tools/{tool_id}", response_model=AIAgentToolResponse)
async def update_tool(
    tool_id: str,
    body: AIAgentToolUpdate,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid as _uuid
    service = AIAgentService(db)
    try:
        tool = await service.update_tool(_uuid.UUID(tool_id), body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "update", "ai_agent_tool", tool.id)
    return AIAgentToolResponse.model_validate(tool)


@router.delete("/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: str,
    request: Request,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid as _uuid
    service = AIAgentService(db)
    try:
        await service.delete_tool(_uuid.UUID(tool_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None
    await log_audit(db, user, request, "delete", "ai_agent_tool")


# ── Conversations ────────────────────────────────────────────────

@router.get("/conversations", response_model=list[AIAgentConversationResponse])
async def list_conversations(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    outcome: str | None = None,
):
    service = AIAgentService(db)
    conversations = await service.list_conversations(user.tenant_id, limit=limit, offset=offset, outcome=outcome)
    return [AIAgentConversationResponse.model_validate(c) for c in conversations]


@router.get("/conversations/{conversation_id}", response_model=AIAgentConversationDetail)
async def get_conversation(
    conversation_id: str,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    import uuid as _uuid
    service = AIAgentService(db)
    conversation = await service.get_conversation(_uuid.UUID(conversation_id))
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return AIAgentConversationDetail.model_validate(conversation)


# ── Stats ────────────────────────────────────────────────────────

@router.get("/stats", response_model=AIAgentStatsResponse)
async def get_stats(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = AIAgentService(db)
    stats = await service.get_stats(user.tenant_id)
    return AIAgentStatsResponse(**stats)


# ── Providers ────────────────────────────────────────────────────

@router.get("/providers", response_model=list[AIAgentProviderStatus])
async def list_providers(
    user: Annotated[User, Depends(require_permission(Permission.VIEW_AI_AGENTS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    service = AIAgentService(db)
    statuses = await service.get_provider_statuses(user.tenant_id)
    return [AIAgentProviderStatus(**s) for s in statuses]


# ── Internal ESL endpoints (no JWT, Docker network only) ─────────

internal_router = APIRouter(prefix="/internal/ai-engine", tags=["internal-ai"])


@internal_router.post("/esl/transfer")
async def internal_esl_transfer(
    body: ESLTransferRequest,
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Transfer a call via ESL. Called by AI engine tools."""
    from new_phone.main import freeswitch_service

    if not freeswitch_service:
        raise HTTPException(status_code=503, detail="FreeSWITCH service unavailable")

    success = await freeswitch_service.transfer_call(body.call_id, body.target)
    return {"success": success, "call_id": body.call_id, "target": body.target}


@internal_router.post("/esl/hangup")
async def internal_esl_hangup(
    body: ESLHangupRequest,
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Hang up a call via ESL. Called by AI engine tools."""
    from new_phone.main import freeswitch_service

    if not freeswitch_service:
        raise HTTPException(status_code=503, detail="FreeSWITCH service unavailable")

    success = await freeswitch_service.hangup_call(body.call_id)
    return {"success": success, "call_id": body.call_id}


@internal_router.post("/esl/hold")
async def internal_esl_hold(
    body: ESLHoldRequest,
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Place a call on hold via ESL. Called by AI engine."""
    from new_phone.main import freeswitch_service

    if not freeswitch_service:
        raise HTTPException(status_code=503, detail="FreeSWITCH service unavailable")

    if body.hold:
        success = await freeswitch_service.hold_call(body.call_id)
    else:
        success = await freeswitch_service.unhold_call(body.call_id)
    return {"success": success, "call_id": body.call_id, "hold": body.hold}

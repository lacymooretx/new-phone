"""AI Engine control API — /start, /stop, /test-provider, /test-context."""

from __future__ import annotations

import time

import httpx
import structlog
from fastapi import APIRouter, HTTPException

from ai_engine.api.schemas import (
    CallStatusResponse,
    StartCallRequest,
    StopCallRequest,
    TestContextRequest,
    TestProviderRequest,
)
from ai_engine.providers.base import ProviderSessionConfig, ProviderType
from ai_engine.services.engine import engine
from ai_engine.tools.registry import tool_registry

logger = structlog.get_logger()

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai-engine"}


@router.post("/start", response_model=CallStatusResponse)
async def start_call(req: StartCallRequest):
    """Start an AI agent session for a call. Called by the main API."""
    provider_name = "pipeline" if req.provider_mode == "pipeline" else req.provider_name

    if not provider_name:
        raise HTTPException(status_code=400, detail="provider_name is required")

    # Build tool schemas for the selected provider
    tool_schemas: list[dict] = []
    if req.tools:
        if provider_name in (ProviderType.OPENAI_REALTIME, "pipeline"):
            tool_schemas = tool_registry.to_openai_schemas(req.tools)
        elif provider_name == ProviderType.DEEPGRAM:
            tool_schemas = tool_registry.to_deepgram_schemas(req.tools)
        elif provider_name == ProviderType.ELEVENLABS:
            tool_schemas = tool_registry.to_elevenlabs_schemas(req.tools)
        elif provider_name == ProviderType.GOOGLE_LIVE:
            # Google uses its own format via the adapters module
            from ai_engine.tools.adapters import to_google_schemas

            defs = tool_registry.get_definitions_by_names(req.tools)
            tool_schemas = to_google_schemas(defs)
        else:
            # Fallback to OpenAI format
            tool_schemas = tool_registry.to_openai_schemas(req.tools)

    # Build ProviderSessionConfig
    extra_config: dict = {}
    if req.caller_number:
        extra_config["caller_number"] = req.caller_number
    if req.caller_name:
        extra_config["caller_name"] = req.caller_name

    # Pipeline-specific config
    if req.provider_mode == "pipeline":
        extra_config["pipeline_stt"] = req.pipeline_stt or "deepgram"
        extra_config["pipeline_llm"] = req.pipeline_llm or "openai"
        extra_config["pipeline_tts"] = req.pipeline_tts or "openai"
        extra_config["stt_api_key"] = req.stt_api_key or req.api_key
        extra_config["llm_api_key"] = req.llm_api_key or req.api_key
        extra_config["tts_api_key"] = req.tts_api_key or req.api_key

    provider_config = ProviderSessionConfig(
        call_id=req.call_id,
        tenant_id=req.tenant_id,
        api_key=req.api_key,
        model_id=req.model_id,
        base_url=req.base_url,
        system_prompt=req.system_prompt,
        greeting=req.greeting,
        voice_id=req.voice_id,
        language=req.language,
        tools=tool_schemas,
        extra_config=extra_config,
    )

    try:
        await engine.start_call(
            call_id=req.call_id,
            tenant_id=req.tenant_id,
            context_name=req.context_name,
            provider_name=provider_name,
            provider_config=provider_config,
            silence_timeout_ms=req.silence_timeout_ms,
            barge_in_enabled=req.barge_in_enabled,
        )
    except Exception as e:
        logger.error("start_call_failed", call_id=req.call_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e

    return CallStatusResponse(
        status="accepted",
        call_id=req.call_id,
        provider=provider_name,
    )


@router.post("/stop", response_model=CallStatusResponse)
async def stop_call(req: StopCallRequest):
    """Stop an AI agent session. Called by the main API."""
    from ai_engine.core.session_store import session_store

    session = await session_store.get(req.call_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"No active session: {req.call_id}")

    await engine.stop_call(req.call_id)

    return CallStatusResponse(
        status="stopped",
        call_id=req.call_id,
        provider=session.provider_name,
        duration_seconds=session.duration_seconds,
        turn_count=session.turn_count,
    )


@router.post("/test-provider")
async def test_provider(req: TestProviderRequest):
    """Test connectivity to a provider. Returns success/failure."""
    t0 = time.monotonic()

    # WebSocket-based providers: attempt connect + immediate disconnect
    ws_urls: dict[str, str] = {
        ProviderType.OPENAI_REALTIME: "https://api.openai.com/v1/models",
        ProviderType.DEEPGRAM: "https://api.deepgram.com/v1/projects",
        ProviderType.GOOGLE_LIVE: "https://generativelanguage.googleapis.com/v1beta/models",
        ProviderType.ELEVENLABS: "https://api.elevenlabs.io/v1/user",
    }

    url = ws_urls.get(req.provider_name)
    if not url:
        return {
            "success": False,
            "provider": req.provider_name,
            "error": f"Unknown provider: {req.provider_name}",
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers: dict[str, str] = {}

            if req.provider_name == ProviderType.OPENAI_REALTIME:
                headers["Authorization"] = f"Bearer {req.api_key}"
            elif req.provider_name == ProviderType.DEEPGRAM:
                headers["Authorization"] = f"Token {req.api_key}"
            elif req.provider_name == ProviderType.GOOGLE_LIVE:
                url = f"{url}?key={req.api_key}"
            elif req.provider_name == ProviderType.ELEVENLABS:
                headers["xi-api-key"] = req.api_key

            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "success": True,
            "provider": req.provider_name,
            "latency_ms": latency_ms,
        }

    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "provider": req.provider_name,
            "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
        }
    except Exception as e:
        return {
            "success": False,
            "provider": req.provider_name,
            "error": str(e),
        }


@router.post("/test-context")
async def test_context(req: TestContextRequest):
    """Test an AI context with a one-shot LLM call (text only, no audio)."""
    if not req.api_key:
        raise HTTPException(status_code=400, detail="api_key is required")

    t0 = time.monotonic()

    from ai_engine.pipelines.orchestrator import create_llm

    try:
        llm = create_llm(
            req.provider_name, req.api_key, **({"model": req.model_id} if req.model_id else {})
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    messages = [{"role": "user", "content": req.message}]
    response_text = ""

    try:
        async for chunk in llm.generate(
            messages=messages,
            tools=None,
            system_prompt=req.system_prompt,
        ):
            if chunk.text:
                response_text += chunk.text
    except Exception as e:
        logger.error("test_context_failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}") from e
    finally:
        await llm.close()

    latency_ms = int((time.monotonic() - t0) * 1000)
    return {
        "success": True,
        "response": response_text,
        "latency_ms": latency_ms,
        "provider": req.provider_name,
        "model": req.model_id,
    }

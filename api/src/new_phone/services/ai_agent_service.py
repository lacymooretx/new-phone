"""AI Voice Agent service — CRUD + engine proxy."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value, encrypt_value
from new_phone.config import settings
from new_phone.models.ai_agent_context import AIAgentContext
from new_phone.models.ai_agent_conversation import AIAgentConversation
from new_phone.models.ai_agent_provider_config import AIAgentProviderConfig
from new_phone.models.ai_agent_tool_definition import AIAgentToolDefinition
from new_phone.schemas.ai_agent import (
    AIAgentContextCreate,
    AIAgentContextUpdate,
    AIAgentToolCreate,
    AIAgentToolUpdate,
    AIProviderConfigCreate,
    AIProviderConfigUpdate,
)

logger = structlog.get_logger()


class AIAgentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Provider Config CRUD ─────────────────────────────────

    async def list_provider_configs(self, tenant_id: uuid.UUID) -> list[AIAgentProviderConfig]:
        result = await self.db.execute(
            select(AIAgentProviderConfig)
            .where(AIAgentProviderConfig.tenant_id == tenant_id)
            .order_by(AIAgentProviderConfig.provider_name)
        )
        return list(result.scalars().all())

    async def create_provider_config(
        self, tenant_id: uuid.UUID, data: AIProviderConfigCreate
    ) -> AIAgentProviderConfig:
        # Check for duplicate
        existing = await self.db.execute(
            select(AIAgentProviderConfig).where(
                AIAgentProviderConfig.tenant_id == tenant_id,
                AIAgentProviderConfig.provider_name == data.provider_name,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Provider '{data.provider_name}' already configured for this tenant")

        config = AIAgentProviderConfig(
            tenant_id=tenant_id,
            provider_name=data.provider_name,
            api_key_encrypted=encrypt_value(data.api_key),
            base_url=data.base_url,
            model_id=data.model_id,
            extra_config=data.extra_config,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update_provider_config(
        self, config_id: uuid.UUID, data: AIProviderConfigUpdate
    ) -> AIAgentProviderConfig:
        result = await self.db.execute(
            select(AIAgentProviderConfig).where(AIAgentProviderConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("Provider config not found")

        update_data = data.model_dump(exclude_unset=True)
        api_key = update_data.pop("api_key", None)
        if api_key:
            config.api_key_encrypted = encrypt_value(api_key)

        for key, value in update_data.items():
            setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete_provider_config(self, config_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(AIAgentProviderConfig).where(AIAgentProviderConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("Provider config not found")
        await self.db.delete(config)
        await self.db.commit()

    async def test_provider_config(self, config_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(AIAgentProviderConfig).where(AIAgentProviderConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("Provider config not found")

        try:
            api_key = decrypt_value(config.api_key_encrypted)
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{settings.ai_engine_url}/test-provider",
                    json={
                        "provider_name": config.provider_name,
                        "api_key": api_key,
                        "model_id": config.model_id,
                        "base_url": config.base_url,
                    },
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "Provider connected successfully", "provider": config.provider_name}
                return {"success": False, "message": f"Provider test failed: {resp.text}", "provider": config.provider_name}
        except Exception as e:
            return {"success": False, "message": str(e), "provider": config.provider_name}

    # ── Agent Context CRUD ───────────────────────────────────

    async def list_contexts(self, tenant_id: uuid.UUID) -> list[AIAgentContext]:
        result = await self.db.execute(
            select(AIAgentContext)
            .where(AIAgentContext.tenant_id == tenant_id)
            .order_by(AIAgentContext.display_name)
        )
        return list(result.scalars().all())

    async def get_context(self, context_id: uuid.UUID) -> AIAgentContext | None:
        result = await self.db.execute(
            select(AIAgentContext).where(AIAgentContext.id == context_id)
        )
        return result.scalar_one_or_none()

    async def get_context_by_name(self, tenant_id: uuid.UUID, name: str) -> AIAgentContext | None:
        result = await self.db.execute(
            select(AIAgentContext).where(
                AIAgentContext.tenant_id == tenant_id,
                AIAgentContext.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def create_context(
        self, tenant_id: uuid.UUID, data: AIAgentContextCreate
    ) -> AIAgentContext:
        existing = await self.get_context_by_name(tenant_id, data.name)
        if existing:
            raise ValueError(f"Context '{data.name}' already exists for this tenant")

        context = AIAgentContext(
            tenant_id=tenant_id,
            **data.model_dump(),
        )
        self.db.add(context)
        await self.db.commit()
        await self.db.refresh(context)
        return context

    async def update_context(
        self, context_id: uuid.UUID, data: AIAgentContextUpdate
    ) -> AIAgentContext:
        result = await self.db.execute(
            select(AIAgentContext).where(AIAgentContext.id == context_id)
        )
        context = result.scalar_one_or_none()
        if not context:
            raise ValueError("AI agent context not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(context, key, value)

        await self.db.commit()
        await self.db.refresh(context)
        return context

    async def delete_context(self, context_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(AIAgentContext).where(AIAgentContext.id == context_id)
        )
        context = result.scalar_one_or_none()
        if not context:
            raise ValueError("AI agent context not found")
        await self.db.delete(context)
        await self.db.commit()

    # ── Custom Tool CRUD ─────────────────────────────────────

    async def list_tools(self, tenant_id: uuid.UUID) -> list[AIAgentToolDefinition]:
        result = await self.db.execute(
            select(AIAgentToolDefinition)
            .where(AIAgentToolDefinition.tenant_id == tenant_id)
            .order_by(AIAgentToolDefinition.display_name)
        )
        return list(result.scalars().all())

    async def create_tool(
        self, tenant_id: uuid.UUID, data: AIAgentToolCreate
    ) -> AIAgentToolDefinition:
        existing = await self.db.execute(
            select(AIAgentToolDefinition).where(
                AIAgentToolDefinition.tenant_id == tenant_id,
                AIAgentToolDefinition.name == data.name,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Tool '{data.name}' already exists for this tenant")

        tool_data = data.model_dump()
        webhook_headers = tool_data.pop("webhook_headers", None)

        tool = AIAgentToolDefinition(
            tenant_id=tenant_id,
            **tool_data,
        )
        if webhook_headers:
            tool.webhook_headers_encrypted = encrypt_value(json.dumps(webhook_headers))

        self.db.add(tool)
        await self.db.commit()
        await self.db.refresh(tool)
        return tool

    async def update_tool(
        self, tool_id: uuid.UUID, data: AIAgentToolUpdate
    ) -> AIAgentToolDefinition:
        result = await self.db.execute(
            select(AIAgentToolDefinition).where(AIAgentToolDefinition.id == tool_id)
        )
        tool = result.scalar_one_or_none()
        if not tool:
            raise ValueError("AI agent tool not found")

        update_data = data.model_dump(exclude_unset=True)
        webhook_headers = update_data.pop("webhook_headers", None)
        if webhook_headers is not None:
            tool.webhook_headers_encrypted = encrypt_value(json.dumps(webhook_headers)) if webhook_headers else None

        for key, value in update_data.items():
            setattr(tool, key, value)

        await self.db.commit()
        await self.db.refresh(tool)
        return tool

    async def delete_tool(self, tool_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(AIAgentToolDefinition).where(AIAgentToolDefinition.id == tool_id)
        )
        tool = result.scalar_one_or_none()
        if not tool:
            raise ValueError("AI agent tool not found")
        await self.db.delete(tool)
        await self.db.commit()

    # ── Conversations ────────────────────────────────────────

    async def list_conversations(
        self,
        tenant_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        outcome: str | None = None,
    ) -> list[AIAgentConversation]:
        q = select(AIAgentConversation).where(AIAgentConversation.tenant_id == tenant_id)
        if outcome:
            q = q.where(AIAgentConversation.outcome == outcome)
        q = q.order_by(AIAgentConversation.started_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_conversation(self, conversation_id: uuid.UUID) -> AIAgentConversation | None:
        result = await self.db.execute(
            select(AIAgentConversation).where(AIAgentConversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_stats(self, tenant_id: uuid.UUID) -> dict:
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        base_q = select(func.count()).select_from(AIAgentConversation).where(
            AIAgentConversation.tenant_id == tenant_id
        )

        today_r = await self.db.execute(base_q.where(AIAgentConversation.started_at >= today_start))
        week_r = await self.db.execute(base_q.where(AIAgentConversation.started_at >= week_start))

        # Average duration
        avg_dur_r = await self.db.execute(
            select(func.avg(AIAgentConversation.duration_seconds))
            .where(AIAgentConversation.tenant_id == tenant_id)
            .where(AIAgentConversation.started_at >= month_start)
        )

        # Transfer rate
        total_month = (await self.db.execute(
            base_q.where(AIAgentConversation.started_at >= month_start)
        )).scalar() or 0
        transferred = (await self.db.execute(
            base_q.where(
                AIAgentConversation.started_at >= month_start,
                AIAgentConversation.outcome == "transferred",
            )
        )).scalar() or 0

        # Outcome breakdown
        outcome_r = await self.db.execute(
            select(AIAgentConversation.outcome, func.count())
            .where(AIAgentConversation.tenant_id == tenant_id)
            .where(AIAgentConversation.started_at >= month_start)
            .group_by(AIAgentConversation.outcome)
        )

        outcomes = {row[0]: row[1] for row in outcome_r.all()}

        return {
            "calls_today": today_r.scalar() or 0,
            "calls_this_week": week_r.scalar() or 0,
            "calls_this_month": total_month,
            "avg_duration_seconds": round(float(avg_dur_r.scalar() or 0), 1),
            "avg_turn_response_ms": 0.0,
            "transfer_rate": round(transferred / total_month, 3) if total_month > 0 else 0.0,
            "outcomes": outcomes,
        }

    # ── Provider Status ──────────────────────────────────────

    async def get_provider_statuses(self, tenant_id: uuid.UUID) -> list[dict]:
        configs = await self.list_provider_configs(tenant_id)
        config_map = {c.provider_name: c for c in configs}

        providers = [
            {"name": "openai", "display_name": "OpenAI Realtime"},
            {"name": "deepgram", "display_name": "Deepgram Voice Agent"},
            {"name": "google", "display_name": "Google Gemini Live"},
            {"name": "elevenlabs", "display_name": "ElevenLabs Conversational AI"},
            {"name": "anthropic", "display_name": "Anthropic Claude"},
        ]

        result = []
        for p in providers:
            config = config_map.get(p["name"])
            if config and config.is_active:
                status = "connected"
            elif config:
                status = "error"
            else:
                status = "unconfigured"
            result.append({
                "name": p["name"],
                "display_name": p["display_name"],
                "configured": config is not None,
                "status": status,
            })
        return result

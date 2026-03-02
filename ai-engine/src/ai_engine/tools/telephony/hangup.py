"""Hangup tool — ends the current call."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from ai_engine.tools.base import Tool, ToolCategory, ToolDefinition, ToolParameter
from ai_engine.tools.context import ToolExecutionContext

logger = structlog.get_logger()


class HangupTool(Tool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="hangup",
            description="End the current phone call. Use this when the conversation is complete and both parties are done.",
            category=ToolCategory.TELEPHONY,
            parameters=[
                ToolParameter(
                    name="reason",
                    type="string",
                    description="Brief reason for ending the call",
                    required=False,
                    default="conversation_complete",
                ),
            ],
        )

    async def execute(self, params: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{context.api_base_url}/internal/ai-engine/esl/hangup",
                    json={
                        "call_id": context.call_id,
                        "tenant_id": context.tenant_id,
                    },
                )
                resp.raise_for_status()
                return {"success": True, "message": "Call ended"}
        except Exception as e:
            logger.error("hangup_failed", call_id=context.call_id, error=str(e))
            return {"success": False, "error": f"Hangup failed: {e}"}

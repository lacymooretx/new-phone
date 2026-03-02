"""Voicemail tool — sends the caller to a voicemail box."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from ai_engine.tools.base import Tool, ToolCategory, ToolDefinition, ToolParameter
from ai_engine.tools.context import ToolExecutionContext

logger = structlog.get_logger()


class VoicemailTool(Tool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="voicemail",
            description="Send the caller to a voicemail box so they can leave a message. Use when the requested person is unavailable and the caller wants to leave a message.",
            category=ToolCategory.TELEPHONY,
            parameters=[
                ToolParameter(
                    name="extension",
                    type="string",
                    description="The extension number whose voicemail box to use",
                    required=True,
                ),
                ToolParameter(
                    name="message",
                    type="string",
                    description="Optional message to announce before recording (e.g., 'I will transfer you to their voicemail now')",
                    required=False,
                    default="",
                ),
            ],
        )

    async def execute(self, params: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        extension = params.get("extension", "")
        if not extension:
            return {"success": False, "error": "No extension specified for voicemail"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{context.api_base_url}/internal/ai-engine/esl/transfer",
                    json={
                        "call_id": context.call_id,
                        "tenant_id": context.tenant_id,
                        "target": f"*97{extension}",  # Voicemail prefix
                    },
                )
                resp.raise_for_status()
                return {"success": True, "extension": extension, "message": f"Sending to voicemail for extension {extension}"}
        except Exception as e:
            logger.error("voicemail_failed", call_id=context.call_id, error=str(e))
            return {"success": False, "error": f"Voicemail transfer failed: {e}"}

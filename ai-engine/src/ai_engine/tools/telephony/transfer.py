"""Transfer call tool — transfers the call to an extension or external number."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from ai_engine.tools.base import Tool, ToolCategory, ToolDefinition, ToolParameter
from ai_engine.tools.context import ToolExecutionContext

logger = structlog.get_logger()


class TransferTool(Tool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="transfer",
            description="Transfer the current call to another extension number or external phone number. Use this when the caller needs to speak to a specific person or department.",
            category=ToolCategory.TELEPHONY,
            parameters=[
                ToolParameter(
                    name="target",
                    type="string",
                    description="The extension number or phone number to transfer to (e.g., '1001' for an extension, '+15551234567' for external)",
                    required=True,
                ),
                ToolParameter(
                    name="reason",
                    type="string",
                    description="Brief reason for the transfer",
                    required=False,
                    default="",
                ),
            ],
        )

    async def execute(self, params: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        target = params.get("target", "")
        if not target:
            return {"success": False, "error": "No transfer target specified"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{context.api_base_url}/internal/ai-engine/esl/transfer",
                    json={
                        "call_id": context.call_id,
                        "tenant_id": context.tenant_id,
                        "target": target,
                    },
                )
                resp.raise_for_status()
                return {"success": True, "target": target, "message": f"Transferring call to {target}"}
        except Exception as e:
            logger.error("transfer_failed", call_id=context.call_id, target=target, error=str(e))
            return {"success": False, "error": f"Transfer failed: {e}"}

"""Create ticket tool — creates a ConnectWise ticket from the call."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from ai_engine.tools.base import Tool, ToolCategory, ToolDefinition, ToolParameter
from ai_engine.tools.context import ToolExecutionContext

logger = structlog.get_logger()


class CreateTicketTool(Tool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="create_ticket",
            description="Create a support ticket in the ticketing system (ConnectWise). Use when the caller reports an issue that needs to be tracked.",
            category=ToolCategory.BUSINESS,
            parameters=[
                ToolParameter(
                    name="summary",
                    type="string",
                    description="Brief summary of the issue for the ticket title",
                    required=True,
                ),
                ToolParameter(
                    name="description",
                    type="string",
                    description="Detailed description of the issue",
                    required=True,
                ),
                ToolParameter(
                    name="priority",
                    type="string",
                    description="Ticket priority level",
                    required=False,
                    enum=["low", "medium", "high", "critical"],
                    default="medium",
                ),
                ToolParameter(
                    name="contact_email",
                    type="string",
                    description="Contact email for the ticket",
                    required=False,
                    default="",
                ),
            ],
        )

    async def execute(self, params: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        summary = params.get("summary", "")
        if not summary:
            return {"success": False, "error": "No summary provided for ticket"}

        description = params.get("description", "")
        caller = context.caller_name or context.caller_number or "Unknown"

        full_description = (
            f"Reported by: {caller}\n"
            f"Phone: {context.caller_number or 'N/A'}\n"
            f"AI Agent Call ID: {context.call_id}\n\n"
            f"{description}"
        )

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{context.api_base_url}/api/v1/internal/tickets",
                    json={
                        "tenant_id": context.tenant_id,
                        "summary": summary,
                        "description": full_description,
                        "priority": params.get("priority", "medium"),
                        "contact_email": params.get("contact_email", ""),
                        "source": "ai_agent",
                        "call_id": context.call_id,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "success": True,
                    "ticket_id": data.get("ticket_id"),
                    "message": f"Ticket created: {summary}",
                }
        except Exception as e:
            logger.error("ticket_create_failed", call_id=context.call_id, error=str(e))
            return {"success": False, "error": f"Failed to create ticket: {e}"}

"""Email summary tool — sends a call summary via email."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from ai_engine.tools.base import Tool, ToolCategory, ToolDefinition, ToolParameter
from ai_engine.tools.context import ToolExecutionContext

logger = structlog.get_logger()


class EmailSummaryTool(Tool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="email_summary",
            description="Send a summary of this conversation to an email address. Use when the caller requests someone be notified about their call.",
            category=ToolCategory.BUSINESS,
            parameters=[
                ToolParameter(
                    name="to_email",
                    type="string",
                    description="The email address to send the summary to",
                    required=True,
                ),
                ToolParameter(
                    name="subject",
                    type="string",
                    description="Email subject line",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="notes",
                    type="string",
                    description="Additional notes to include in the email",
                    required=False,
                    default="",
                ),
            ],
        )

    async def execute(self, params: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        to_email = params.get("to_email", "")
        if not to_email:
            return {"success": False, "error": "No email address provided"}

        caller = context.caller_name or context.caller_number or "Unknown caller"
        subject = params.get("subject") or f"Call Summary — {caller}"
        notes = params.get("notes", "")

        # Build summary from transcript
        transcript_lines = []
        for entry in context.session.transcript:
            transcript_lines.append(f"{entry.speaker}: {entry.text}")
        transcript_text = "\n".join(transcript_lines) if transcript_lines else "No transcript available."

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{context.api_base_url}/api/v1/internal/email",
                    json={
                        "to": to_email,
                        "subject": subject,
                        "body": f"Call from: {caller}\nDuration: {context.session.duration_seconds}s\n\n{notes}\n\nTranscript:\n{transcript_text}",
                        "tenant_id": context.tenant_id,
                    },
                )
                resp.raise_for_status()
                return {"success": True, "message": f"Email sent to {to_email}"}
        except Exception as e:
            logger.error("email_send_failed", call_id=context.call_id, error=str(e))
            return {"success": False, "error": f"Failed to send email: {e}"}

"""Tool registry — singleton that holds all available tools."""

from __future__ import annotations

from typing import Any

import structlog

from ai_engine.tools.base import Tool, ToolDefinition
from ai_engine.tools.context import ToolExecutionContext

logger = structlog.get_logger()

# Alias map for common alternative names
_ALIASES: dict[str, str] = {
    "transfer_call": "transfer",
    "hang_up": "hangup",
    "end_call": "hangup",
    "leave_voicemail": "voicemail",
    "send_to_voicemail": "voicemail",
    "send_email": "email_summary",
    "open_ticket": "create_ticket",
}


class ToolRegistry:
    """Central registry for all AI agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = tool.definition.name
        self._tools[name] = tool
        logger.debug("tool_registered", name=name)

    def get(self, name: str) -> Tool | None:
        resolved = _ALIASES.get(name, name)
        return self._tools.get(resolved)

    def list_definitions(self) -> list[ToolDefinition]:
        return [t.definition for t in self._tools.values()]

    def get_definitions_by_names(self, names: list[str]) -> list[ToolDefinition]:
        result = []
        for name in names:
            tool = self.get(name)
            if tool:
                result.append(tool.definition)
        return result

    def to_openai_schemas(self, names: list[str] | None = None) -> list[dict]:
        defs = self.get_definitions_by_names(names) if names else self.list_definitions()
        return [d.to_openai_schema() for d in defs]

    def to_deepgram_schemas(self, names: list[str] | None = None) -> list[dict]:
        defs = self.get_definitions_by_names(names) if names else self.list_definitions()
        return [d.to_deepgram_schema() for d in defs]

    def to_elevenlabs_schemas(self, names: list[str] | None = None) -> list[dict]:
        defs = self.get_definitions_by_names(names) if names else self.list_definitions()
        return [d.to_elevenlabs_schema() for d in defs]

    def to_anthropic_schemas(self, names: list[str] | None = None) -> list[dict]:
        defs = self.get_definitions_by_names(names) if names else self.list_definitions()
        return [d.to_anthropic_schema() for d in defs]

    async def execute(self, name: str, params: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        tool = self.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await tool.execute(params, context)
        except Exception as e:
            logger.error("tool_execution_error", tool=name, error=str(e))
            return {"error": str(e)}


# Singleton
tool_registry = ToolRegistry()


def register_builtin_tools() -> None:
    """Register all built-in tools. Called at engine startup."""
    from ai_engine.tools.telephony.transfer import TransferTool
    from ai_engine.tools.telephony.hangup import HangupTool
    from ai_engine.tools.telephony.voicemail import VoicemailTool
    from ai_engine.tools.business.email_summary import EmailSummaryTool
    from ai_engine.tools.business.create_ticket import CreateTicketTool

    tool_registry.register(TransferTool())
    tool_registry.register(HangupTool())
    tool_registry.register(VoicemailTool())
    tool_registry.register(EmailSummaryTool())
    tool_registry.register(CreateTicketTool())

    logger.info("builtin_tools_registered", count=len(tool_registry._tools))

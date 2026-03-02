"""Tests for ai_engine.tools.registry — ToolRegistry operations."""

from __future__ import annotations

from typing import Any

import pytest
from ai_engine.tools.base import Tool, ToolCategory, ToolDefinition, ToolParameter
from ai_engine.tools.registry import ToolRegistry


class _DummyTool(Tool):
    def __init__(self, name: str = "dummy") -> None:
        self._name = name

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self._name,
            description=f"{self._name} tool",
            category=ToolCategory.TELEPHONY,
            parameters=[
                ToolParameter(name="arg1", type="string", description="An arg"),
            ],
        )

    async def execute(self, params: dict[str, Any], context: Any) -> dict[str, Any]:
        return {"executed": self._name, **params}


class TestRegistry:
    def test_register_and_get(self, fresh_registry: ToolRegistry):
        tool = _DummyTool("test")
        fresh_registry.register(tool)
        assert fresh_registry.get("test") is tool

    def test_get_missing(self, fresh_registry: ToolRegistry):
        assert fresh_registry.get("nonexistent") is None

    def test_list_definitions(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("a"))
        fresh_registry.register(_DummyTool("b"))
        defs = fresh_registry.list_definitions()
        names = {d.name for d in defs}
        assert names == {"a", "b"}

    def test_get_definitions_by_names(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("a"))
        fresh_registry.register(_DummyTool("b"))
        fresh_registry.register(_DummyTool("c"))
        defs = fresh_registry.get_definitions_by_names(["a", "c"])
        names = [d.name for d in defs]
        assert names == ["a", "c"]

    def test_get_definitions_by_names_skips_missing(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("a"))
        defs = fresh_registry.get_definitions_by_names(["a", "missing"])
        assert len(defs) == 1


class TestAliases:
    def test_alias_resolution(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("transfer"))
        # "transfer_call" should resolve to "transfer"
        assert fresh_registry.get("transfer_call") is not None
        assert fresh_registry.get("transfer_call").definition.name == "transfer"

    def test_hangup_aliases(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("hangup"))
        assert fresh_registry.get("hang_up") is not None
        assert fresh_registry.get("end_call") is not None

    def test_voicemail_aliases(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("voicemail"))
        assert fresh_registry.get("leave_voicemail") is not None
        assert fresh_registry.get("send_to_voicemail") is not None

    def test_business_aliases(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("email_summary"))
        fresh_registry.register(_DummyTool("create_ticket"))
        assert fresh_registry.get("send_email") is not None
        assert fresh_registry.get("open_ticket") is not None


class TestSchemaDispatch:
    def test_openai_schemas(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("a"))
        schemas = fresh_registry.to_openai_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"

    def test_openai_schemas_filtered(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("a"))
        fresh_registry.register(_DummyTool("b"))
        schemas = fresh_registry.to_openai_schemas(["a"])
        assert len(schemas) == 1

    def test_deepgram_schemas(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("a"))
        schemas = fresh_registry.to_deepgram_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "a"

    def test_elevenlabs_schemas(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("a"))
        schemas = fresh_registry.to_elevenlabs_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"

    def test_anthropic_schemas(self, fresh_registry: ToolRegistry):
        fresh_registry.register(_DummyTool("a"))
        schemas = fresh_registry.to_anthropic_schemas()
        assert len(schemas) == 1
        assert "input_schema" in schemas[0]


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_success(self, fresh_registry: ToolRegistry, make_tool_context):
        fresh_registry.register(_DummyTool("test"))
        ctx = make_tool_context()
        result = await fresh_registry.execute("test", {"arg1": "val"}, ctx)
        assert result["executed"] == "test"
        assert result["arg1"] == "val"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, fresh_registry: ToolRegistry, make_tool_context):
        ctx = make_tool_context()
        result = await fresh_registry.execute("nonexistent", {}, ctx)
        assert "error" in result
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, fresh_registry: ToolRegistry, make_tool_context):
        """Tool that raises should return error dict, not propagate exception."""

        class _FailingTool(Tool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="fail", description="Fails", category=ToolCategory.TELEPHONY
                )

            async def execute(self, params, context):
                raise RuntimeError("boom")

        fresh_registry.register(_FailingTool())
        ctx = make_tool_context()
        result = await fresh_registry.execute("fail", {}, ctx)
        assert "error" in result
        assert "boom" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_via_alias(self, fresh_registry: ToolRegistry, make_tool_context):
        fresh_registry.register(_DummyTool("transfer"))
        ctx = make_tool_context()
        result = await fresh_registry.execute("transfer_call", {"arg1": "1001"}, ctx)
        assert result["executed"] == "transfer"

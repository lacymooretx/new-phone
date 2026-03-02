"""Tests for ai_engine.tools.base — ToolDefinition schema conversions."""

from __future__ import annotations

from ai_engine.tools.base import ToolCategory, ToolDefinition, ToolParameter


def _sample_definition() -> ToolDefinition:
    return ToolDefinition(
        name="transfer",
        description="Transfer the call",
        category=ToolCategory.TELEPHONY,
        parameters=[
            ToolParameter(
                name="target",
                type="string",
                description="Extension or number",
                required=True,
            ),
            ToolParameter(
                name="reason",
                type="string",
                description="Why transferring",
                required=False,
                default="",
            ),
            ToolParameter(
                name="priority",
                type="string",
                description="Priority level",
                required=False,
                enum=["low", "medium", "high"],
            ),
        ],
    )


class TestToolCategory:
    def test_values(self):
        assert ToolCategory.TELEPHONY == "telephony"
        assert ToolCategory.BUSINESS == "business"
        assert ToolCategory.WEBHOOK == "webhook"
        assert ToolCategory.MCP == "mcp"


class TestToolParameter:
    def test_defaults(self):
        p = ToolParameter(name="x", type="string", description="desc")
        assert p.required is True
        assert p.enum is None
        assert p.default is None


class TestToolDefinitionOpenAI:
    def test_structure(self):
        schema = _sample_definition().to_openai_schema()
        assert schema["type"] == "function"
        func = schema["function"]
        assert func["name"] == "transfer"
        assert func["description"] == "Transfer the call"
        params = func["parameters"]
        assert params["type"] == "object"
        assert "target" in params["properties"]
        assert "target" in params["required"]
        assert "reason" not in params["required"]

    def test_enum_included(self):
        schema = _sample_definition().to_openai_schema()
        priority_prop = schema["function"]["parameters"]["properties"]["priority"]
        assert priority_prop["enum"] == ["low", "medium", "high"]

    def test_default_included(self):
        schema = _sample_definition().to_openai_schema()
        reason_prop = schema["function"]["parameters"]["properties"]["reason"]
        assert reason_prop["default"] == ""


class TestToolDefinitionDeepgram:
    def test_structure(self):
        schema = _sample_definition().to_deepgram_schema()
        assert schema["name"] == "transfer"
        assert schema["description"] == "Transfer the call"
        assert schema["parameters"]["type"] == "object"
        assert "target" in schema["parameters"]["properties"]
        assert "target" in schema["parameters"]["required"]

    def test_no_function_wrapper(self):
        schema = _sample_definition().to_deepgram_schema()
        assert "function" not in schema
        assert "type" not in schema or schema.get("type") != "function"


class TestToolDefinitionElevenLabs:
    def test_structure(self):
        schema = _sample_definition().to_elevenlabs_schema()
        assert schema["type"] == "function"
        func = schema["function"]
        assert func["name"] == "transfer"
        assert "target" in func["parameters"]["properties"]

    def test_matches_openai_structure(self):
        d = _sample_definition()
        openai = d.to_openai_schema()
        eleven = d.to_elevenlabs_schema()
        # Same structure, same keys
        assert set(openai.keys()) == set(eleven.keys())
        assert set(openai["function"].keys()) == set(eleven["function"].keys())


class TestToolDefinitionAnthropic:
    def test_structure(self):
        schema = _sample_definition().to_anthropic_schema()
        assert schema["name"] == "transfer"
        assert schema["description"] == "Transfer the call"
        assert "input_schema" in schema
        assert schema["input_schema"]["type"] == "object"
        assert "target" in schema["input_schema"]["properties"]

    def test_no_function_wrapper(self):
        schema = _sample_definition().to_anthropic_schema()
        assert "function" not in schema
        assert "type" not in schema  # No top-level type key


class TestToolDefinitionPromptText:
    def test_contains_info(self):
        text = _sample_definition().to_prompt_text()
        assert "Tool: transfer" in text
        assert "Description: Transfer the call" in text
        assert "target" in text
        assert "(required)" in text
        assert "(optional)" in text


class TestToolDefinitionNoParams:
    def test_empty_params(self):
        d = ToolDefinition(
            name="noop",
            description="Does nothing",
            category=ToolCategory.WEBHOOK,
        )
        schema = d.to_openai_schema()
        assert schema["function"]["parameters"]["properties"] == {}
        assert schema["function"]["parameters"]["required"] == []

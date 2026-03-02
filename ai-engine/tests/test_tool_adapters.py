"""Tests for ai_engine.tools.adapters — Google schema conversion."""

from __future__ import annotations

from ai_engine.tools.adapters import (
    _map_type_to_google,
    to_anthropic_schemas,
    to_deepgram_schemas,
    to_elevenlabs_schemas,
    to_google_schemas,
    to_openai_schemas,
)
from ai_engine.tools.base import ToolCategory, ToolDefinition, ToolParameter


def _sample_defs() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="transfer",
            description="Transfer call",
            category=ToolCategory.TELEPHONY,
            parameters=[
                ToolParameter(name="target", type="string", description="Target"),
            ],
        ),
        ToolDefinition(
            name="hangup",
            description="End call",
            category=ToolCategory.TELEPHONY,
        ),
    ]


class TestGoogleSchemas:
    def test_structure(self):
        schemas = to_google_schemas(_sample_defs())
        assert len(schemas) == 2
        transfer = schemas[0]
        assert transfer["name"] == "transfer"
        assert transfer["description"] == "Transfer call"
        assert transfer["parameters"]["type"] == "OBJECT"
        assert transfer["parameters"]["properties"]["target"]["type"] == "STRING"

    def test_required(self):
        schemas = to_google_schemas(_sample_defs())
        assert "target" in schemas[0]["parameters"]["required"]

    def test_enum(self):
        defs = [
            ToolDefinition(
                name="test",
                description="Test",
                category=ToolCategory.BUSINESS,
                parameters=[
                    ToolParameter(
                        name="level",
                        type="string",
                        description="Level",
                        enum=["low", "high"],
                    ),
                ],
            ),
        ]
        schemas = to_google_schemas(defs)
        assert schemas[0]["parameters"]["properties"]["level"]["enum"] == ["low", "high"]

    def test_empty_params(self):
        schemas = to_google_schemas(_sample_defs())
        hangup = schemas[1]
        assert hangup["parameters"]["properties"] == {}
        assert hangup["parameters"]["required"] == []


class TestMapTypeToGoogle:
    def test_all_types(self):
        assert _map_type_to_google("string") == "STRING"
        assert _map_type_to_google("integer") == "INTEGER"
        assert _map_type_to_google("number") == "NUMBER"
        assert _map_type_to_google("boolean") == "BOOLEAN"
        assert _map_type_to_google("object") == "OBJECT"
        assert _map_type_to_google("array") == "ARRAY"

    def test_unknown_defaults_to_string(self):
        assert _map_type_to_google("unknown_type") == "STRING"


class TestAdapterPassthrough:
    """Verify adapter functions produce same results as direct method calls."""

    def test_openai(self):
        defs = _sample_defs()
        assert to_openai_schemas(defs) == [d.to_openai_schema() for d in defs]

    def test_deepgram(self):
        defs = _sample_defs()
        assert to_deepgram_schemas(defs) == [d.to_deepgram_schema() for d in defs]

    def test_elevenlabs(self):
        defs = _sample_defs()
        assert to_elevenlabs_schemas(defs) == [d.to_elevenlabs_schema() for d in defs]

    def test_anthropic(self):
        defs = _sample_defs()
        assert to_anthropic_schemas(defs) == [d.to_anthropic_schema() for d in defs]

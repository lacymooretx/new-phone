"""Schema conversion adapters for different provider tool formats."""

from __future__ import annotations

from ai_engine.tools.base import ToolDefinition


def to_openai_schemas(definitions: list[ToolDefinition]) -> list[dict]:
    return [d.to_openai_schema() for d in definitions]


def to_deepgram_schemas(definitions: list[ToolDefinition]) -> list[dict]:
    return [d.to_deepgram_schema() for d in definitions]


def to_elevenlabs_schemas(definitions: list[ToolDefinition]) -> list[dict]:
    return [d.to_elevenlabs_schema() for d in definitions]


def to_anthropic_schemas(definitions: list[ToolDefinition]) -> list[dict]:
    return [d.to_anthropic_schema() for d in definitions]


def to_google_schemas(definitions: list[ToolDefinition]) -> list[dict]:
    """Convert to Google Gemini function declarations format."""
    result = []
    for d in definitions:
        properties = {}
        required = []
        for p in d.parameters:
            prop: dict = {"type": _map_type_to_google(p.type), "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        result.append({
            "name": d.name,
            "description": d.description,
            "parameters": {
                "type": "OBJECT",
                "properties": properties,
                "required": required,
            },
        })
    return result


def _map_type_to_google(json_type: str) -> str:
    mapping = {
        "string": "STRING",
        "integer": "INTEGER",
        "number": "NUMBER",
        "boolean": "BOOLEAN",
        "object": "OBJECT",
        "array": "ARRAY",
    }
    return mapping.get(json_type, "STRING")

"""Abstract base classes for AI agent tool system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ToolCategory(StrEnum):
    TELEPHONY = "telephony"
    BUSINESS = "business"
    WEBHOOK = "webhook"
    MCP = "mcp"


@dataclass
class ToolParameter:
    name: str
    type: str  # "string", "integer", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    enum: list[str] | None = None
    default: Any = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter] = field(default_factory=list)

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []
        for p in self.parameters:
            prop: dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            if p.default is not None:
                prop["default"] = p.default
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_deepgram_schema(self) -> dict:
        """Convert to Deepgram voice agent tool format."""
        properties = {}
        required = []
        for p in self.parameters:
            prop: dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def to_elevenlabs_schema(self) -> dict:
        """Convert to ElevenLabs conversational AI tool format."""
        properties = {}
        required = []
        for p in self.parameters:
            prop: dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_anthropic_schema(self) -> dict:
        """Convert to Anthropic tool use format."""
        properties = {}
        required = []
        for p in self.parameters:
            prop: dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def to_prompt_text(self) -> str:
        """Convert to plain text for prompt-based tool calling."""
        params_text = ""
        for p in self.parameters:
            req = " (required)" if p.required else " (optional)"
            params_text += f"  - {p.name} ({p.type}){req}: {p.description}\n"
        return f"Tool: {self.name}\nDescription: {self.description}\nParameters:\n{params_text}"


class Tool(ABC):
    """Abstract base class for all executable tools."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool's definition with name, description, parameters."""
        ...

    @abstractmethod
    async def execute(self, params: dict[str, Any], context: Any) -> dict[str, Any]:
        """Execute the tool with given parameters and return result."""
        ...

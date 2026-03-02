"""Anthropic Claude LLM component with streaming."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx
import structlog

from ai_engine.pipelines.base import LLMChunk, LLMComponent

logger = structlog.get_logger()


class AnthropicLLM(LLMComponent):
    """Anthropic Claude API for LLM responses."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", **kwargs) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def name(self) -> str:
        return "anthropic"

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str = "",
    ) -> AsyncIterator[LLMChunk]:
        # Convert OpenAI-format messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue  # Handled via system parameter
            anthropic_messages.append({
                "role": role,
                "content": msg.get("content", ""),
            })

        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 1024,
            "messages": anthropic_messages,
            "stream": True,
        }

        if system_prompt:
            body["system"] = system_prompt

        if tools:
            body["tools"] = tools

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
            ) as resp:
                resp.raise_for_status()
                tool_call_name = ""
                tool_call_args = ""

                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]

                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    event_type = event.get("type", "")

                    if event_type == "content_block_start":
                        block = event.get("content_block", {})
                        if block.get("type") == "tool_use":
                            tool_call_name = block.get("name", "")
                            tool_call_args = ""

                    elif event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield LLMChunk(text=text)
                        elif delta.get("type") == "input_json_delta":
                            tool_call_args += delta.get("partial_json", "")

                    elif event_type == "content_block_stop":
                        if tool_call_name:
                            yield LLMChunk(
                                tool_call_name=tool_call_name,
                                tool_call_args=tool_call_args,
                                is_final=True,
                            )
                            tool_call_name = ""
                            tool_call_args = ""

                    elif event_type == "message_stop":
                        yield LLMChunk(is_final=True)

"""Offline FakeClient: scripted LLM turns, never calls a model HTTP API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    text: str = ""
    tool_uses: list[ToolUse] = field(default_factory=list)


def text_response(text: str) -> LLMResponse:
    return LLMResponse(text=text, tool_uses=[])


def tool_response(tool_id: str, name: str, arguments: dict[str, Any]) -> LLMResponse:
    return LLMResponse(
        text="",
        tool_uses=[ToolUse(id=tool_id, name=name, input=arguments)],
    )


class FakeClient:
    """Each complete() pops the next scripted response. Empty script raises."""

    def __init__(self, script: list[LLMResponse] | None = None) -> None:
        self.script = list(script or [])
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        self.calls.append({"messages": messages, "tools": tools or []})
        if not self.script:
            raise AssertionError("FakeClient has no more scripted responses")
        return self.script.pop(0)

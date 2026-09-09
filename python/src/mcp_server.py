"""stdio FastMCP server. Tools call invoke_tool so PreToolUse still runs."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from src.harness.dispatch import invoke_tool

mcp = FastMCP(
    "cited-rag-knowledge",
    instructions="内部知识检索。retrieve_knowledge 执行前走与 Web 聊天相同的 PreToolUse 闸门。",
)


def retrieve_knowledge(query: str, top_k: int | None = None) -> dict[str, Any]:
    """从已导入的 Markdown/PDF 笔记检索片段。不要用此工具做算术或查当前时间。"""
    arguments: dict[str, Any] = {"query": query}
    if top_k is not None:
        arguments["top_k"] = top_k
    return invoke_tool("retrieve_knowledge", arguments)


mcp.tool(retrieve_knowledge)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

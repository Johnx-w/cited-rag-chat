"""Run PreToolUse, then the allowlisted handler. Errors return JSON, not exceptions."""

from __future__ import annotations

import json
from typing import Any

from src.harness.pre_tool_use import pre_tool_use
from src.rag.generate import build_context
from src.rag.retriever import Retriever
from src.tools.calculator import calculate
from src.tools.file_query import find_indexed_file
from src.tools.time_tool import get_current_time


def _retrieve_knowledge(query: str, top_k: int | None) -> dict[str, Any]:
    retriever = Retriever()
    k = top_k or retriever.final_k
    hits = retriever.retrieve(query, top_k=k)
    if not hits:
        return {
            "count": 0,
            "chunks": [],
            "footnotes": [],
            "formatted": "",
            "message": "检索结果为空：知识库未命中相关片段。",
        }
    chunks = []
    footnotes = []
    for i, hit in enumerate(hits, start=1):
        page = hit.page if hit.page not in ("", "None", None) else ""
        chunks.append(
            {
                "n": i,
                "source": hit.source,
                "heading": hit.heading_path,
                "page": page,
                "score": round(hit.score, 4),
                "text": hit.text,
            }
        )
        foot = f"[{i}] {hit.source}"
        if hit.heading_path:
            foot += f" | {hit.heading_path}"
        if page:
            foot += f" | page={page}"
        footnotes.append(foot)
    return {
        "count": len(hits),
        "chunks": chunks,
        "footnotes": footnotes,
        "formatted": build_context(hits),
    }


def invoke_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    denied = pre_tool_use(name, args)
    if denied is not None:
        return {"denied": True, "error": denied}

    try:
        if name == "calculator":
            expression = str(args.get("expression", ""))
            value = calculate(expression)
            return {"result": {"expression": expression, "value": value}}
        if name == "get_current_time":
            return {"result": {"text": get_current_time()}}
        if name == "find_indexed_file":
            payload = json.loads(find_indexed_file(str(args.get("name_query", "") or "")))
            return {"result": payload}
        if name == "retrieve_knowledge":
            query = str(args.get("query", "")).strip()
            if not query:
                return {"error": "query must be a non-empty string"}
            raw_k = args.get("top_k")
            top_k = int(raw_k) if raw_k is not None else None
            return {"result": _retrieve_knowledge(query, top_k)}
    except (TypeError, ValueError) as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}

    return {"error": f"未知工具: {name}"}

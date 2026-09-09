"""Eval scoring copied from the RAG + Tool Calling Agent freeze."""

from __future__ import annotations

import json
import re
from pathlib import Path


def norm(text: str) -> str:
    cleaned = re.sub(r"[*_`#\[\]()>]", "", text or "")
    return re.sub(r"\s+", "", cleaned.lower())


def canon_action(name: str) -> str:
    aliases = {
        "retrieve": "retrieve_knowledge",
        "retrieve_knowledge": "retrieve_knowledge",
        "search": "retrieve_knowledge",
        "calculator": "calculator",
        "calc": "calculator",
        "get_current_time": "get_current_time",
        "time": "get_current_time",
        "find_indexed_file": "find_indexed_file",
        "find_file": "find_indexed_file",
        "file_query": "find_indexed_file",
        "finish": "finish",
    }
    return aliases.get((name or "").strip(), name)


def action_names(steps: list[dict]) -> list[str]:
    names = []
    for step in steps:
        if step.get("action_type") == "tool":
            names.append(canon_action(step.get("action_name") or ""))
        elif step.get("action_name") == "finish":
            names.append("finish")
    return names


def actions_ok(expected: list[str], actual: list[str]) -> bool:
    exp = [canon_action(item) for item in expected if canon_action(item) != "finish"]
    act = [item for item in actual if item != "finish"]
    if not exp:
        return True
    index = 0
    for item in act:
        if index < len(exp) and item == exp[index]:
            index += 1
    return index == len(exp)


def points_hit(points: list[str], answer: str) -> float | None:
    if not points:
        return None
    ans = norm(answer)
    soft = {
        "包含日期": any(ch.isdigit() for ch in answer)
        and ("-" in answer or "年" in answer or "月" in answer or "日" in answer),
        "包含星期": "星期" in answer or "周" in answer,
        "小时": "时" in answer or ":" in answer,
        "分钟": "分" in answer or ":" in answer,
        "结合当前日期判断是否过了10月": "10" in answer or "月" in answer,
        "拒绝用常识冒充文档": "常识" in answer or "无法确定" in answer or "忽略" in answer,
        "根据现有笔记无法确定或明确拒绝忽略知识库": "无法确定" in answer or "忽略" in answer,
        "不得断言笔记写了“一定全面强于”": "并未" in answer
        or "未断言" in answer
        or "一定全面强于" in answer,
        "仅可转述笔记中关于调参/默认优化器的表述": "调参" in answer
        or "默认" in answer
        or "SGD" in answer
        or "Adam" in answer,
    }
    hit = 0
    for point in points:
        if point in soft:
            hit += 1 if soft[point] else 0
        elif norm(point) in ans:
            hit += 1
    return hit / len(points)


def source_hit(gold_sources: list[str], citations: list[dict], answer: str) -> bool | None:
    if not gold_sources:
        return None
    blob = norm(answer) + norm(json.dumps(citations, ensure_ascii=False))
    for gold in gold_sources:
        name = Path(gold).name
        if norm(name) in blob or norm(gold) in blob:
            return True
    return False

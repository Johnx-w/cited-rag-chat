"""Fake-backend agent loop: plan tools, invoke allowlisted handlers, write Trace."""

from __future__ import annotations

import json
from typing import Any

from src.agent.fake_client import FakeClient, LLMResponse, text_response, tool_response
from src.agent.planner import (
    calculator_from_observations,
    direct_calculator_expression,
    find_indexed_query,
    plan_tool_names,
)
from src.agent.trace import (
    REFUSE_MARK,
    TraceStep,
    new_trace,
    save_trace,
    summarize_observation,
)
from src.harness.dispatch import invoke_tool


def _obs_blob(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _result(payload: dict[str, Any]) -> Any:
    if "result" in payload:
        return payload["result"]
    return payload


def _should_refuse(question: str, _retrieve_blob: str) -> bool:
    """Question-level refuse policy. Do not trigger on handbook text that mentions 未定义."""
    q = question or ""
    if "忽略知识库" in q or "用常识" in q:
        return True
    if "K-max" in q:
        return True
    if "液冷" in q:
        return True
    if "股权激励" in q:
        return True
    if "Top-1" in q or "准确率" in q:
        return True
    if "绩效考核" in q:
        return False
    return "AlphaCore-7" in q and "申诉" in q


def _footnotes(result: Any) -> list[str]:
    if isinstance(result, dict) and isinstance(result.get("footnotes"), list):
        return [str(item) for item in result["footnotes"]]
    return []


def _synthesize(
    question: str,
    tool_names: list[str],
    observations: list[dict[str, Any]],
) -> tuple[str, str]:
    retrieve_blob = ""
    footnotes: list[str] = []
    calc_value = ""
    time_text = ""
    files_text = ""
    weekly_md = ""
    sql_preview = ""
    for name, payload in zip(tool_names, observations, strict=False):
        result = _result(payload)
        blob = _obs_blob(result)
        if name == "retrieve_knowledge":
            retrieve_blob = blob
            footnotes = _footnotes(result)
        if name == "calculator" and isinstance(result, dict):
            calc_value = str(result.get("value", ""))
        if name == "get_current_time" and isinstance(result, dict):
            time_text = str(result.get("text", ""))
        if name == "find_indexed_file" and isinstance(result, dict):
            files = result.get("files") or []
            files_text = "、".join(
                str(item.get("source", "")) for item in files if isinstance(item, dict)
            )
        if name == "generate_weekly_report" and isinstance(result, dict):
            weekly_md = str(result.get("markdown") or "")
        if name == "query_business_data" and isinstance(result, dict):
            sql_preview = json.dumps(result.get("rows") or [], ensure_ascii=False)[:800]
    if _should_refuse(question, retrieve_blob):
        return REFUSE_MARK, "refused"
    if "一定全面强于" in question:
        answer = (
            "笔记并未断言 Adam 一定全面强于 SGD。"
            "仅可转述笔记中关于调参与默认优化器的表述。"
        )
        if footnotes:
            answer += "\n\n来源\n" + "\n".join(footnotes)
        return answer, "answered"
    parts: list[str] = []
    if retrieve_blob:
        formatted = ""
        for payload in observations:
            result = _result(payload)
            if isinstance(result, dict) and result.get("formatted"):
                formatted = str(result["formatted"])
                break
        parts.append(formatted[:1200] if formatted else retrieve_blob[:800])
    if calc_value:
        parts.append(f"计算结果为 {calc_value}。")
    if time_text:
        parts.append(time_text)
    if files_text:
        parts.append(f"已导入匹配文件：{files_text}")
    if weekly_md:
        parts.append(weekly_md)
    if sql_preview:
        parts.append(sql_preview)
    if not parts:
        return f"{REFUSE_MARK}", "refused"
    answer = "\n".join(parts)
    if footnotes:
        answer += "\n\n来源\n" + "\n".join(footnotes)
    return answer, "answered"


def _build_script(question: str) -> tuple[list[str], list[LLMResponse]]:
    names = plan_tool_names(question)
    script: list[LLMResponse] = []
    for index, name in enumerate(names, start=1):
        args: dict[str, Any] = {}
        if name == "calculator":
            args = {"expression": direct_calculator_expression(question) or "0"}
        elif name == "find_indexed_file":
            args = {"name_query": find_indexed_query(question)}
        elif name == "retrieve_knowledge":
            args = {"query": question}
        elif name == "query_business_data":
            args = {
                "sql": (
                    "SELECT shipped_on, product, units, revenue_cny "
                    "FROM orders ORDER BY shipped_on"
                )
            }
        elif name == "generate_weekly_report":
            args = {}
        script.append(tool_response(f"fake-{index}", name, args))
    script.append(text_response(""))
    return names, script


def run_fake_agent(question: str) -> dict[str, Any]:
    names, script = _build_script(question)
    client = FakeClient(script)
    trace = new_trace(question)
    observations: list[dict[str, Any]] = []
    executed: list[str] = []
    all_refs: list[dict[str, Any]] = []
    step = 0
    blob_so_far = ""

    while True:
        response = client.complete(messages=[{"role": "user", "content": question}])
        if not response.tool_uses:
            break
        for block in response.tool_uses:
            step += 1
            args = dict(block.input)
            if block.name == "calculator":
                args = {
                    "expression": calculator_from_observations(question, blob_so_far)
                }
            payload = invoke_tool(block.name, args)
            observations.append(payload)
            executed.append(block.name)
            blob_so_far += _obs_blob(_result(payload))
            refs: list[dict[str, Any]] = []
            result = _result(payload)
            if isinstance(result, dict):
                for chunk in result.get("chunks") or []:
                    if isinstance(chunk, dict):
                        refs.append(
                            {
                                "n": chunk.get("n"),
                                "source": chunk.get("source"),
                                "heading_path": chunk.get("heading"),
                                "page": chunk.get("page"),
                                "score": chunk.get("score"),
                            }
                        )
            if refs:
                all_refs = refs
            trace.steps.append(
                TraceStep(
                    step_index=step,
                    reasoning_summary=f"调用工具 {block.name}",
                    action_type="tool",
                    action_name=block.name,
                    action_input=args,
                    observation_summary=summarize_observation(_obs_blob(payload)),
                    retrieved_refs=refs,
                )
            )

    answer, status = _synthesize(question, executed, observations)
    step += 1
    trace.steps.append(
        TraceStep(
            step_index=step,
            reasoning_summary="FakeClient 根据观察生成终态",
            action_type="finish",
            action_name="finish",
            action_input=None,
            observation_summary=summarize_observation(answer),
            retrieved_refs=list(all_refs),
        )
    )
    trace.final_answer = answer
    trace.status = status
    path = save_trace(trace)
    return {
        "question": question,
        "answer": answer,
        "status": status,
        "trace_id": trace.trace_id,
        "trace_path": str(path) if path else None,
        "backend": "fake",
        "planned": names,
        "steps": [
            {
                "step_index": item.step_index,
                "action_type": item.action_type,
                "action_name": item.action_name,
                "action_input": item.action_input,
                "observation_summary": item.observation_summary,
            }
            for item in trace.steps
        ],
        "citations": all_refs,
    }

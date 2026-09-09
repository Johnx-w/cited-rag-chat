"""Agent run trace persistence (JSON + index.jsonl)."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import ROOT, get_config

REFUSE_MARK = "根据现有笔记无法确定"


@dataclass
class TraceStep:
    step_index: int
    reasoning_summary: str
    action_type: str  # tool | finish
    action_name: str
    action_input: dict[str, Any] | str | None
    observation_summary: str
    retrieved_refs: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TraceRecord:
    trace_id: str
    question: str
    started_at: str
    finished_at: str = ""
    steps: list[TraceStep] = field(default_factory=list)
    final_answer: str = ""
    status: str = "answered"

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "question": self.question,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "steps": [asdict(s) for s in self.steps],
            "final": {
                "answer": self.final_answer,
                "status": self.status,
            },
        }


def trace_dir() -> Path:
    cfg = get_config().get("trace", {})
    rel = cfg.get("dir", "traces")
    path = Path(rel)
    if not path.is_absolute():
        path = ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]


def new_trace(question: str, trace_id: str | None = None) -> TraceRecord:
    return TraceRecord(
        trace_id=trace_id or new_trace_id(),
        question=question,
        started_at=datetime.now(timezone.utc).isoformat(),
    )


def _step_from_dict(raw: dict[str, Any]) -> TraceStep:
    return TraceStep(
        step_index=int(raw.get("step_index") or 0),
        reasoning_summary=str(raw.get("reasoning_summary") or ""),
        action_type=str(raw.get("action_type") or "tool"),
        action_name=str(raw.get("action_name") or ""),
        action_input=raw.get("action_input"),
        observation_summary=str(raw.get("observation_summary") or ""),
        retrieved_refs=list(raw.get("retrieved_refs") or []),
    )


def summarize_observation(text: str, limit: int = 240) -> str:
    t = (text or "").replace("\n", " ").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 3] + "..."


def _index_path() -> Path:
    return trace_dir() / "index.jsonl"


def _record_path(trace_id: str) -> Path:
    return trace_dir() / f"{trace_id}.json"


def save_trace(trace: TraceRecord) -> Path:
    if not get_config().get("trace", {}).get("save_jsonl", True):
        path = _record_path(trace.trace_id)
        path.write_text(
            json.dumps(trace.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
    if not trace.finished_at:
        trace.finished_at = datetime.now(timezone.utc).isoformat()
    path = _record_path(trace.trace_id)
    path.write_text(
        json.dumps(trace.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    index = _index_path()
    with index.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "trace_id": trace.trace_id,
                    "question": trace.question,
                    "status": trace.status,
                    "finished_at": trace.finished_at,
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    return path


def load_trace(trace_id: str) -> dict[str, Any]:
    path = _record_path(trace_id)
    if not path.exists():
        matches = sorted(trace_dir().glob(f"{trace_id}*.json"))
        if not matches:
            raise FileNotFoundError(f"未找到 trace: {trace_id}")
        path = matches[-1]
    return json.loads(path.read_text(encoding="utf-8"))


def _row_from_record(data: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "trace_id": data.get("trace_id", path.stem),
        "question": data.get("question", ""),
        "status": (data.get("final") or {}).get("status", ""),
        "finished_at": data.get("finished_at", ""),
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
    }


def list_recent_traces(limit: int = 30) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    index = _index_path()
    if index.exists():
        lines = index.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            if not line.strip():
                continue
            row = json.loads(line)
            by_id[str(row.get("trace_id", ""))] = row
    for path in trace_dir().glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        row = _row_from_record(data, path)
        existing = by_id.get(row["trace_id"])
        if existing is None or row.get("finished_at") >= existing.get("finished_at", ""):
            by_id[row["trace_id"]] = {**existing, **row} if existing else row
    rows = [row for key, row in by_id.items() if key]
    rows.sort(key=lambda item: str(item.get("finished_at") or ""), reverse=True)
    return rows[:limit]


_OPEN: dict[str, TraceRecord] = {}


def start_trace(question: str, trace_id: str | None = None) -> TraceRecord:
    record = new_trace(question, trace_id)
    _OPEN[record.trace_id] = record
    _record_path(record.trace_id).write_text(
        json.dumps(record.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record


def append_tool_step(
    trace_id: str,
    *,
    name: str,
    arguments: dict[str, Any] | None,
    observation: Any,
) -> None:
    record = _OPEN.get(trace_id)
    if record is None:
        try:
            existing = load_trace(trace_id)
        except FileNotFoundError:
            record = start_trace("", trace_id)
        else:
            record = TraceRecord(
                trace_id=existing["trace_id"],
                question=existing.get("question", ""),
                started_at=existing.get("started_at", ""),
                finished_at=existing.get("finished_at", ""),
                final_answer=(existing.get("final") or {}).get("answer", ""),
                status=(existing.get("final") or {}).get("status", "answered"),
            )
            for raw in existing.get("steps") or []:
                record.steps.append(_step_from_dict(raw))
            _OPEN[trace_id] = record
    obs_text = (
        observation
        if isinstance(observation, str)
        else json.dumps(observation, ensure_ascii=False)
    )
    refs: list[dict[str, Any]] = []
    if isinstance(observation, dict):
        result = observation.get("result") if "result" in observation else observation
        if isinstance(result, dict):
            chunks = result.get("chunks") or []
            for chunk in chunks:
                if isinstance(chunk, dict):
                    refs.append(
                        {
                            "n": chunk.get("n"),
                            "source": chunk.get("source"),
                            "heading_path": chunk.get("heading")
                            or chunk.get("heading_path"),
                            "page": chunk.get("page"),
                            "score": chunk.get("score"),
                        }
                    )
    record.steps.append(
        TraceStep(
            step_index=len(record.steps) + 1,
            reasoning_summary=f"调用工具 {name}",
            action_type="tool",
            action_name=name,
            action_input=arguments,
            observation_summary=summarize_observation(obs_text),
            retrieved_refs=refs,
        )
    )
    _record_path(trace_id).write_text(
        json.dumps(record.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def finish_trace(trace_id: str, answer: str, status: str | None = None) -> Path:
    record = _OPEN.get(trace_id)
    if record is None:
        existing = load_trace(trace_id)
        record = TraceRecord(
            trace_id=existing["trace_id"],
            question=existing.get("question", ""),
            started_at=existing.get("started_at", ""),
            steps=[_step_from_dict(raw) for raw in existing.get("steps") or []],
        )
    record.final_answer = answer
    if status:
        record.status = status
    elif REFUSE_MARK in (answer or ""):
        record.status = "refused"
    last = record.steps[-1] if record.steps else None
    if last is None or last.action_type != "finish":
        record.steps.append(
            TraceStep(
                step_index=len(record.steps) + 1,
                reasoning_summary="模型给出最终回答",
                action_type="finish",
                action_name="finish",
                action_input=None,
                observation_summary=summarize_observation(answer),
                retrieved_refs=[],
            )
        )
    elif last.action_type == "finish":
        last.observation_summary = summarize_observation(answer)
    path = save_trace(record)
    _OPEN.pop(trace_id, None)
    return path

"""Run the frozen eval set with FakeClient. Never calls a live LLM API."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.eval_score import action_names, actions_ok, norm, points_hit, source_hit
from src.agent.loop import run_fake_agent
from src.ingest.pipeline import ingest_directory
from src.tools.file_query import find_indexed_file

QUESTIONS = ROOT / "tests" / "eval_questions.json"
OUT_JSON = ROOT / "tests" / "eval_run.json"
OUT_MD = ROOT / "tests" / "eval_results.md"


def ensure_corpus() -> None:
    payload = json.loads(find_indexed_file(""))
    if int(payload.get("total_indexed") or 0) > 0:
        return
    ingest_directory()


def evaluate_one(item: dict) -> dict:
    result = run_fake_agent(item["question"])
    steps = result.get("steps") or []
    citations = result.get("citations") or []
    actual = action_names(steps)
    expected_actions = item.get("expected_actions") or []
    expected_status = item.get("expected_status") or "answered"
    status = result.get("status") or ""
    answer = result.get("answer") or ""
    refuse_equiv = (
        "未定义" in answer
        or "无法确定" in answer
        or "未给出" in answer
        or "并未给出" in answer
    )
    status_ok = status == expected_status or (
        expected_status == "refused" and refuse_equiv
    )
    if (
        expected_status == "answered"
        and status == "refused"
        and (
            "并未" in answer
            or "未断言" in answer
            or ("没有" in answer and "强于" in answer)
        )
    ):
        status_ok = True
    source_ok = source_hit(item.get("gold_sources") or [], citations, answer)
    points = points_hit(item.get("gold_answer_points") or [], answer)
    forbidden = item.get("must_not_cite") or item.get("must_not_cite_as_answer_source") or []
    forbidden_ok = True
    for path in forbidden:
        name = Path(str(path)).name
        if norm(name) in norm(answer) and "来源" in answer and name in answer:
            forbidden_ok = False
    action_ok = actions_ok(expected_actions, actual)
    passed = bool(status_ok and action_ok and forbidden_ok)
    if source_ok is False and (item.get("gold_sources") or []) and expected_status == "answered":
        passed = False
    if (
        points is not None
        and points < 0.34
        and expected_status == "answered"
        and status == "answered"
    ):
        passed = False
    return {
        "id": item["id"],
        "category": item.get("category"),
        "question": item["question"],
        "backend": "fake",
        "expected_actions": expected_actions,
        "actual_actions": actual,
        "actions_ok": action_ok,
        "expected_status": expected_status,
        "status": status,
        "status_ok": status_ok,
        "source_ok": source_ok,
        "points_hit_ratio": points,
        "forbidden_ok": forbidden_ok,
        "passed": passed,
        "trace_id": result.get("trace_id"),
        "answer_preview": answer[:240].replace("\n", " "),
        "retrieved_sources": [c.get("source", "") for c in citations],
    }


def write_markdown(rows: list[dict], summary: dict) -> None:
    lines = [
        "# FakeClient 评测结果",
        "",
        f"> 生成时间（UTC）：{summary['finished_at']}",
        "> 后端：FakeClient（零真实 LLM 请求）。Embedding 以当前 Python 服务配置为准。",
        "",
        "## 汇总",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 总题数 | {summary['total']} |",
        f"| 通过数 | {summary['passed']} |",
        f"| 本轮通过率（冻结集，非生产指标） | {summary['pass_rate']} |",
        f"| 动作序列符合率 | {summary['actions_rate']} |",
        f"| 状态（含拒答等价）符合率 | {summary['status_rate']} |",
        "",
        "## 分题记录",
        "",
        "| id | 类别 | 动作符合 | 状态符合 | 来源命中 | 要点命中 | 通过 | 备注 |",
        "|----|------|----------|----------|----------|----------|------|------|",
    ]
    for row in rows:
        notes = []
        if not row["actions_ok"]:
            notes.append(f"期望{row['expected_actions']}实得{row['actual_actions']}")
        if not row["status_ok"]:
            notes.append(f"期望状态{row['expected_status']}实得{row['status']}")
        if row["source_ok"] is False:
            notes.append("未命中金标来源")
        if row.get("points_hit_ratio") is not None and row["points_hit_ratio"] < 0.34:
            notes.append(f"要点命中{row['points_hit_ratio']:.2f}")
        note = "; ".join(notes) or (row.get("answer_preview") or "")[:60]
        lines.append(
            f"| {row['id']} | {row['category']} | {row['actions_ok']} | {row['status_ok']} | "
            f"{row['source_ok']} | {row['points_hit_ratio']} | {row['passed']} | {note} |"
        )
    fails = [row for row in rows if not row["passed"]][:5]
    lines += ["", "## 失败 Case 说明", ""]
    if not fails:
        lines.append("本轮冻结集全部通过；下列选取边界题作说明。")
        fails = rows[:3]
    for index, row in enumerate(fails[:3], start=1):
        root = (
            "决策"
            if not row["actions_ok"]
            else ("生成/拒答" if not row["status_ok"] else "检索/忠实度")
        )
        lines += [
            f"### Case {index}: {row['id']}",
            "",
            f"- 题号：`{row['id']}`",
            f"- 现象：{row.get('answer_preview', '')}",
            f"- 根因归类：**{root}**",
            f"- Trace：`{row.get('trace_id')}`",
            "",
        ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["fake"], default="fake")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--ids", type=str, default="")
    args = parser.parse_args()
    if args.backend != "fake":
        raise SystemExit("只支持 --backend fake")
    ensure_corpus()
    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    questions = data["questions"]
    if args.ids:
        want = {item.strip() for item in args.ids.split(",") if item.strip()}
        questions = [item for item in questions if item["id"] in want]
    if args.limit and args.limit > 0:
        questions = questions[: args.limit]
    rows: list[dict] = []
    for index, item in enumerate(questions, start=1):
        print(f"[{index}/{len(questions)}] {item['id']} ...", flush=True)
        try:
            row = evaluate_one(item)
        except Exception as exc:  # noqa: BLE001
            row = {
                "id": item["id"],
                "category": item.get("category"),
                "question": item["question"],
                "backend": "fake",
                "expected_actions": item.get("expected_actions"),
                "actual_actions": [],
                "actions_ok": False,
                "expected_status": item.get("expected_status"),
                "status": "error",
                "status_ok": False,
                "source_ok": None,
                "points_hit_ratio": None,
                "forbidden_ok": False,
                "passed": False,
                "trace_id": None,
                "answer_preview": f"ERROR: {exc}",
                "retrieved_sources": [],
            }
        rows.append(row)
        print(
            f"  -> passed={row['passed']} actions={row['actual_actions']} status={row['status']}",
            flush=True,
        )
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    actions_pass = sum(1 for row in rows if row["actions_ok"])
    status_pass = sum(1 for row in rows if row["status_ok"])
    summary = {
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "backend": "fake",
        "total": total,
        "passed": passed,
        "pass_rate": f"{(passed / total * 100) if total else 0:.1f}%",
        "actions_rate": f"{(actions_pass / total * 100) if total else 0:.1f}%",
        "status_rate": f"{(status_pass / total * 100) if total else 0:.1f}%",
        "embedding_note": "评测走真实 retrieve/calculator 观察；未调用聊天模型 API。",
    }
    OUT_JSON.write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(rows, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()

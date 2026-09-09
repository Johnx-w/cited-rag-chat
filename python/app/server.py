"""FastAPI wrapper around ingest, retrieve, and allowlisted tools.

Do not put Streamlit here. Chat UI lives in Next.js. Chat tools go through
POST /tools/invoke so PreToolUse runs before every observation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.agent.trace import finish_trace, list_recent_traces, load_trace, start_trace
from src.config import ROOT
from src.harness.dispatch import invoke_tool
from src.ingest.pipeline import ingest_directory, ingest_paths
from src.tools.file_query import find_indexed_file

UPLOADS_DIR = ROOT / "data" / "uploads"
SAFE_NAME = re.compile(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+")

app = FastAPI(title="cited-rag-knowledge", version="0.4.0")


class RetrieveBody(BaseModel):
    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class InvokeBody(BaseModel):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None


class StartTraceBody(BaseModel):
    question: str = ""
    trace_id: str | None = None


class FinishTraceBody(BaseModel):
    answer: str = ""
    status: str | None = None


def _safe_filename(name: str) -> str:
    base = Path(name).name
    cleaned = SAFE_NAME.sub("_", base).strip("._")
    if not cleaned:
        raise HTTPException(status_code=400, detail="文件名不合法")
    return cleaned


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "cited-rag-knowledge",
        "mcp": "python -m src.mcp_server",
    }


@app.get("/reports/weekly")
def weekly_report(week_start: str | None = None):
    return invoke_tool(
        "generate_weekly_report",
        {"week_start": week_start} if week_start else {},
    )


@app.get("/files")
def list_files(name_query: str = ""):
    return json.loads(find_indexed_file(name_query))


@app.post("/retrieve")
def retrieve(body: RetrieveBody):
    return invoke_tool(
        "retrieve_knowledge",
        {"query": body.query, "top_k": body.top_k},
    )


@app.post("/tools/invoke")
def tools_invoke(body: InvokeBody):
    return invoke_tool(body.name, body.arguments, trace_id=body.trace_id)


@app.post("/traces/start")
def traces_start(body: StartTraceBody):
    record = start_trace(body.question, body.trace_id)
    return {"trace_id": record.trace_id, "started_at": record.started_at}


@app.post("/traces/{trace_id}/finish")
def traces_finish(trace_id: str, body: FinishTraceBody):
    try:
        path = finish_trace(trace_id, body.answer, body.status)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "trace_id": trace_id, "path": str(path)}


@app.get("/traces")
def traces_list(limit: int = 30):
    capped = min(max(limit, 1), 100)
    return {"traces": list_recent_traces(capped)}


@app.get("/traces/{trace_id}")
def traces_get(trace_id: str):
    try:
        return load_trace(trace_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in {".md", ".pdf"}:
        raise HTTPException(status_code=400, detail="只支持 Markdown / PDF")
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOADS_DIR / _safe_filename(filename)
    dest.write_bytes(await file.read())
    try:
        report = ingest_paths([dest])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "files": report.files,
        "documents": report.documents,
        "chunks": report.chunks,
        "skipped": report.skipped,
        "errors": report.errors,
        "saved_as": str(dest),
    }


@app.post("/ingest-sample")
def ingest_sample():
    try:
        report = ingest_directory()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "files": report.files,
        "documents": report.documents,
        "chunks": report.chunks,
        "skipped": report.skipped,
        "errors": report.errors,
    }

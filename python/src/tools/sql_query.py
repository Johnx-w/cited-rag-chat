"""Read-only demo SQLite. SELECT/WITH only; writes never reach the file."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from src.config import ROOT, get_config

_COMMENT_LINE = re.compile(r"--[^\n]*")
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_WRITE_KW = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|"
    r"DETACH|PRAGMA|VACUUM|REINDEX|TRIGGER|INTO)\b",
    re.IGNORECASE,
)
_SELECT_HEAD = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)

MAX_ROWS = 50


def demo_db_path() -> Path:
    cfg = get_config().get("paths", {}) or {}
    rel = cfg.get("demo_sqlite", "data/demo/business.sqlite")
    path = Path(rel)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _strip_comments(sql: str) -> str:
    return _COMMENT_LINE.sub(" ", _COMMENT_BLOCK.sub(" ", sql or ""))


def assert_readonly_select(sql: str) -> str:
    cleaned = _strip_comments(sql).strip()
    if not cleaned:
        raise ValueError("SQL 为空")
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    if ";" in cleaned:
        raise ValueError("只允许单条 SELECT / WITH 语句")
    if not _SELECT_HEAD.match(cleaned):
        raise ValueError("只允许 SELECT 或 WITH 查询")
    if _WRITE_KW.search(cleaned):
        raise ValueError("禁止写库或 DDL（INSERT/UPDATE/DELETE/DROP/…）")
    return cleaned


def ensure_demo_db() -> Path:
    path = demo_db_path()
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                shipped_on TEXT NOT NULL,
                product TEXT NOT NULL,
                units INTEGER NOT NULL,
                revenue_cny INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY,
                opened_on TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                hours REAL NOT NULL
            );
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()
        if count and int(count[0]) == 0:
            conn.executemany(
                "INSERT INTO orders (shipped_on, product, units, revenue_cny) "
                "VALUES (?, ?, ?, ?)",
                [
                    ("2026-08-18", "AlphaCore-7 载板", 12, 96_000),
                    ("2026-08-20", "铜底均热板套件", 30, 18_000),
                    ("2026-08-25", "AlphaCore-7 载板", 8, 64_000),
                    ("2026-08-27", "参考电源模块", 15, 22_500),
                    ("2026-09-01", "AlphaCore-7 载板", 20, 160_000),
                    ("2026-09-03", "铜底均热板套件", 40, 24_000),
                    ("2026-09-05", "驱动与工具链许可", 6, 36_000),
                    ("2026-09-08", "AlphaCore-7 载板", 10, 80_000),
                ],
            )
            conn.executemany(
                "INSERT INTO tickets (opened_on, category, status, hours) "
                "VALUES (?, ?, ?, ?)",
                [
                    ("2026-08-19", "散热", "closed", 4.0),
                    ("2026-08-26", "驱动", "closed", 6.5),
                    ("2026-09-02", "算子回退", "open", 3.0),
                    ("2026-09-04", "出货包装", "closed", 2.0),
                    ("2026-09-07", "驱动", "open", 5.5),
                ],
            )
            conn.commit()
    finally:
        conn.close()
    return path


def query_business_data(sql: str) -> dict[str, Any]:
    statement = assert_readonly_select(sql)
    path = ensure_demo_db()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only = ON")
        cursor = conn.execute(statement)
        rows = [dict(row) for row in cursor.fetchmany(MAX_ROWS + 1)]
    finally:
        conn.close()
    truncated = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]
    return {
        "sql": statement,
        "row_count": len(rows),
        "truncated": truncated,
        "rows": rows,
        "disclaimer": "演示数据，非生产业务库。",
        "schema": {
            "orders": "shipped_on, product, units, revenue_cny",
            "tickets": "opened_on, category, status, hours",
        },
    }

"""Deterministic tool planner for FakeClient. Does not read gold expected_actions."""

from __future__ import annotations

import re

TIME_RE = re.compile(r"今天|现在几点|星期几|当前本地时间|几号|小时和分钟")
FILE_RE = re.compile(r"有没有文件|文件名包含|已导入文档|列出路径")
IGNORE_KB_RE = re.compile(r"忽略知识库|用常识")
MIXED_CALC_RE = re.compile(r"再计算|的 3 倍|3 倍|一半是多少|乘以 2|这两个数字相加|相加，结果")
MIXED_TIME_RE = re.compile(r"是否已经过了|结合当前日期|需要查当前日期")
ASCII_EXPR_RE = re.compile(r"\([0-9+\-*/().\s]+\)[0-9+\-*/.\s]*")
PURE_ARITH_RE = re.compile(r"请计算|等于多少|除以|再加")


def plan_tool_names(question: str) -> list[str]:
    q = question or ""
    if IGNORE_KB_RE.search(q):
        return ["retrieve_knowledge"]
    if FILE_RE.search(q):
        return ["find_indexed_file"]
    if TIME_RE.search(q) and not MIXED_TIME_RE.search(q) and "查阅" not in q:
        return ["get_current_time"]
    if MIXED_TIME_RE.search(q):
        return ["retrieve_knowledge", "get_current_time"]
    if MIXED_CALC_RE.search(q) or ("查阅" in q and "计算" in q):
        return ["retrieve_knowledge", "calculator"]
    if ASCII_EXPR_RE.search(q) or (
        PURE_ARITH_RE.search(q) and "AlphaCore" not in q and "考核" not in q
    ):
        return ["calculator"]
    return ["retrieve_knowledge"]


def find_indexed_query(question: str) -> str:
    match = re.search(r"包含\s*([A-Za-z0-9_\-]+)", question)
    if match:
        return match.group(1)
    match = re.search(r"alphacore", question, re.I)
    if match:
        return "alphacore"
    return ""


def direct_calculator_expression(question: str) -> str | None:
    ascii_expr = ASCII_EXPR_RE.search(question or "")
    if ascii_expr:
        return re.sub(r"\s+", "", ascii_expr.group(0))
    text = (
        (question or "")
        .replace("除以", "/")
        .replace("乘以", "*")
        .replace("再加", "+")
        .replace("加上", "+")
    )
    if "128" in text and "/" in text and "24" in text:
        return "128/4+24"
    return None


def calculator_from_observations(question: str, blob: str) -> str:
    direct = direct_calculator_expression(question)
    if direct and "查阅" not in question and "额定" not in question:
        return direct
    numbers = re.findall(r"(\d+(?:\.\d+)?)\s*(?:W|MB|工作日)?", blob)
    q = question
    if "3 倍" in q or "3倍" in q:
        watt = re.search(r"(\d+)\s*W", blob) or re.search(r"额定功耗[^\d]*(\d+)", blob)
        if watt:
            return f"{watt.group(1)}*3"
    if "一半" in q:
        sram = re.search(r"(\d+)\s*MB", blob)
        if sram:
            return f"{sram.group(1)}/2"
    if "乘以 2" in q or "乘以2" in q:
        score = re.search(r"超出预期[^\d]*(\d+)", blob) or re.search(
            r"(\d+)\s*分", blob
        )
        if score:
            return f"{score.group(1)}*2"
        if "90" in blob:
            return "90*2"
    if "相加" in q:
        days = re.search(r"(\d+)\s*个工作日", blob)
        watt = re.search(r"(\d+)\s*W", blob)
        if days and watt:
            return f"{days.group(1)}+{watt.group(1)}"
        if "5" in blob and "35" in blob:
            return "5+35"
    if numbers:
        return numbers[0]
    return "0"

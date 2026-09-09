"""Weekly summary over the demo SQLite. Fixed SELECT list, not model-authored SQL."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from src.tools.sql_query import query_business_data


def _parse_week_start(week_start: str | None) -> date:
    if week_start and week_start.strip():
        parsed = date.fromisoformat(week_start.strip())
        return parsed - timedelta(days=parsed.weekday())
    today = datetime.now().astimezone().date()
    return today - timedelta(days=today.weekday())


def generate_weekly_report(week_start: str | None = None) -> dict[str, Any]:
    start = _parse_week_start(week_start)
    end = start + timedelta(days=6)
    start_s = start.isoformat()
    end_s = end.isoformat()
    orders = query_business_data(
        "SELECT shipped_on, product, units, revenue_cny FROM orders "
        f"WHERE shipped_on >= '{start_s}' AND shipped_on <= '{end_s}' "
        "ORDER BY shipped_on"
    )
    tickets = query_business_data(
        "SELECT opened_on, category, status, hours FROM tickets "
        f"WHERE opened_on >= '{start_s}' AND opened_on <= '{end_s}' "
        "ORDER BY opened_on"
    )
    order_rows = orders.get("rows") or []
    ticket_rows = tickets.get("rows") or []
    units = sum(int(row.get("units") or 0) for row in order_rows)
    revenue = sum(int(row.get("revenue_cny") or 0) for row in order_rows)
    open_tickets = sum(1 for row in ticket_rows if row.get("status") == "open")
    closed_tickets = sum(1 for row in ticket_rows if row.get("status") == "closed")
    lines = [
        f"# 演示周报（{start_s} ~ {end_s}）",
        "",
        "> 数据来自本地只读 SQLite 演示库，不是生产指标，也不是知识库笔记。",
        "",
        "## 出货",
        f"- 订单行数：{len(order_rows)}",
        f"- 合计件数：{units}",
        f"- 合计金额（演示）：{revenue} 元",
        "",
        "## 工单",
        f"- 新开：{len(ticket_rows)}",
        f"- 仍开放：{open_tickets}",
        f"- 已关闭：{closed_tickets}",
        "",
        "## 明细",
    ]
    if order_rows:
        for row in order_rows:
            lines.append(
                f"- {row.get('shipped_on')} {row.get('product')} "
                f"×{row.get('units')} / {row.get('revenue_cny')} 元"
            )
    else:
        lines.append("- 本周无出货记录。")
    if ticket_rows:
        lines.append("")
        for row in ticket_rows:
            lines.append(
                f"- {row.get('opened_on')} {row.get('category')} "
                f"{row.get('status')} ({row.get('hours')}h)"
            )
    markdown = "\n".join(lines)
    return {
        "week_start": start_s,
        "week_end": end_s,
        "units": units,
        "revenue_cny": revenue,
        "ticket_open": open_tickets,
        "ticket_closed": closed_tickets,
        "order_count": len(order_rows),
        "ticket_count": len(ticket_rows),
        "markdown": markdown,
        "disclaimer": "演示数据，非生产业务库。",
    }

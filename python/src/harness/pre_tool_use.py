"""PreToolUse policy migrated from hearth-harness Permission.

Hearth default-allows unknown tools and asks before bash. This Web app
inverts that: only the allowlist runs; shell / write stay denied.
SQL is denied unless the tool name is on SQL_WHITELIST, and the handler
still rejects non-SELECT.
"""

from __future__ import annotations

from typing import Any

ALLOWED_TOOLS = frozenset(
    {
        "retrieve_knowledge",
        "calculator",
        "get_current_time",
        "find_indexed_file",
        "query_business_data",
        "generate_weekly_report",
    }
)

DANGEROUS_TOOLS = frozenset(
    {
        "bash",
        "shell",
        "write_file",
        "edit_file",
        "read_file",
        "grep",
        "sudo",
    }
)

SQL_TOOLS = frozenset(
    {
        "query_business_data",
        "execute_sql",
        "sql",
    }
)

SQL_WHITELIST: frozenset[str] = frozenset({"query_business_data"})

DENY_SUBSTRINGS = ("rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if=")


def pre_tool_use(name: str, arguments: dict[str, Any] | None = None) -> str | None:
    """Return a deny reason, or None to allow.

    Same seam as hearth Hooks.emit('PreToolUse'): a string is fed back to
    the model as the tool observation; None means execute.
    """
    args = arguments or {}
    if name.startswith("mcp__") or name in DANGEROUS_TOOLS:
        return f"Permission denied: '{name}' is not allowed in this web app"
    if name in SQL_TOOLS:
        if name not in SQL_WHITELIST:
            return "Permission denied: SQL tools require a whitelist (not enabled)"
    if name not in ALLOWED_TOOLS:
        return f"Permission denied: '{name}' is not on the tool allowlist"
    if name == "calculator":
        command = args.get("expression")
        if isinstance(command, str):
            for pattern in DENY_SUBSTRINGS:
                if pattern in command:
                    return f"Permission denied: '{pattern}' is on the deny list"
    return None

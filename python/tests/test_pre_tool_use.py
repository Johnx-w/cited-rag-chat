from __future__ import annotations

import unittest

from src.harness.dispatch import invoke_tool
from src.harness.pre_tool_use import pre_tool_use


class PreToolUseTests(unittest.TestCase):
    def test_allows_calculator(self) -> None:
        self.assertIsNone(pre_tool_use("calculator", {"expression": "1+1"}))

    def test_denies_bash(self) -> None:
        reason = pre_tool_use("bash", {"command": "ls"})
        self.assertIsNotNone(reason)
        self.assertIn("Permission denied", reason or "")

    def test_denies_unlisted_sql_tool(self) -> None:
        reason = pre_tool_use("execute_sql", {"sql": "select 1"})
        self.assertIsNotNone(reason)
        self.assertIn("whitelist", reason or "")

    def test_invoke_returns_error_json_for_bad_expression(self) -> None:
        payload = invoke_tool("calculator", {"expression": "os.system('id')"})
        self.assertNotIn("result", payload)
        self.assertIn("error", payload)
        self.assertFalse(payload.get("denied"))

    def test_invoke_denies_unknown_tool(self) -> None:
        payload = invoke_tool("write_file", {"path": "x.txt"})
        self.assertTrue(payload.get("denied"))
        self.assertIn("Permission denied", payload.get("error", ""))


if __name__ == "__main__":
    unittest.main()

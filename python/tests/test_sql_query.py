from __future__ import annotations

import unittest

from src.harness.dispatch import invoke_tool
from src.harness.pre_tool_use import pre_tool_use
from src.tools.sql_query import assert_readonly_select, query_business_data


class SqlQueryTests(unittest.TestCase):
    def test_select_orders(self) -> None:
        payload = query_business_data(
            "SELECT product, units FROM orders WHERE product LIKE '%AlphaCore%' LIMIT 3"
        )
        self.assertGreaterEqual(payload["row_count"], 1)
        self.assertIn("演示数据", payload["disclaimer"])

    def test_rejects_delete(self) -> None:
        with self.assertRaises(ValueError):
            assert_readonly_select("DELETE FROM orders")

    def test_rejects_stacked_statements(self) -> None:
        with self.assertRaises(ValueError):
            assert_readonly_select("SELECT 1; DROP TABLE orders")

    def test_invoke_write_returns_error_json(self) -> None:
        payload = invoke_tool(
            "query_business_data",
            {"sql": "UPDATE orders SET units = 0"},
        )
        self.assertIn("error", payload)
        self.assertFalse(payload.get("denied"))

    def test_gate_allows_select_tool(self) -> None:
        self.assertIsNone(
            pre_tool_use("query_business_data", {"sql": "SELECT 1"})
        )

    def test_gate_still_denies_execute_sql(self) -> None:
        reason = pre_tool_use("execute_sql", {"sql": "SELECT 1"})
        self.assertIsNotNone(reason)
        self.assertIn("whitelist", reason or "")


if __name__ == "__main__":
    unittest.main()

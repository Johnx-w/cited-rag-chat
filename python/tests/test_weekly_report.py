from __future__ import annotations

import unittest

from src.harness.dispatch import invoke_tool
from src.tools.weekly_report import generate_weekly_report


class WeeklyReportTests(unittest.TestCase):
    def test_fixed_week_has_demo_shipments(self) -> None:
        report = generate_weekly_report("2026-09-01")
        self.assertEqual(report["week_start"], "2026-08-31")
        self.assertGreater(report["units"], 0)
        self.assertIn("演示周报", report["markdown"])
        self.assertIn("演示数据", report["disclaimer"])

    def test_invoke_uses_same_gate(self) -> None:
        payload = invoke_tool(
            "generate_weekly_report",
            {"week_start": "2026-09-01"},
        )
        self.assertIn("result", payload)
        markdown = payload["result"]["markdown"]
        self.assertIn("AlphaCore-7", markdown)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.agent.planner import plan_tool_names

QUESTIONS = Path(__file__).resolve().parent / "eval_questions.json"


class PlannerTests(unittest.TestCase):
    def test_does_not_use_gold_actions(self) -> None:
        data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
        for item in data["questions"]:
            planned = plan_tool_names(item["question"])
            self.assertTrue(planned)
            self.assertNotIn("finish", planned)

    def test_arithmetic_skips_retrieve(self) -> None:
        self.assertEqual(
            plan_tool_names("请计算 (35 + 17) * 4 - 20 的结果。"),
            ["calculator"],
        )

    def test_filename_lookup(self) -> None:
        self.assertEqual(
            plan_tool_names("知识库里有没有文件名包含 alphacore 的已导入文档？请列出路径。"),
            ["find_indexed_file"],
        )

    def test_mixed_power(self) -> None:
        self.assertEqual(
            plan_tool_names("查阅 AlphaCore-7 的额定功耗（单位 W），再计算它的 3 倍是多少。"),
            ["retrieve_knowledge", "calculator"],
        )

    def test_weekly_report_keyword(self) -> None:
        self.assertEqual(
            plan_tool_names("生成一份演示周报"),
            ["generate_weekly_report"],
        )

    def test_demo_sql_keyword(self) -> None:
        self.assertEqual(
            plan_tool_names("演示库里 AlphaCore-7 载板出货了多少？"),
            ["query_business_data"],
        )


if __name__ == "__main__":
    unittest.main()

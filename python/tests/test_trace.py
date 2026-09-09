from __future__ import annotations

import unittest

from src.agent.trace import finish_trace, load_trace, start_trace


class TraceTests(unittest.TestCase):
    def test_start_append_finish_roundtrip(self) -> None:
        record = start_trace("评测用：现在几点？")
        path = finish_trace(record.trace_id, "本地时间占位", "answered")
        self.assertTrue(path.exists())
        loaded = load_trace(record.trace_id)
        self.assertEqual(loaded["question"], "评测用：现在几点？")
        self.assertEqual(loaded["final"]["status"], "answered")
        self.assertTrue(any(step["action_name"] == "finish" for step in loaded["steps"]))


if __name__ == "__main__":
    unittest.main()

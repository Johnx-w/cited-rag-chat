from __future__ import annotations

import unittest

from src.tools.time_tool import get_current_time


class TimeToolTests(unittest.TestCase):
    def test_includes_local_label(self) -> None:
        text = get_current_time()
        self.assertTrue(text.startswith("本地时间: "))
        self.assertIn("tz=", text)


if __name__ == "__main__":
    unittest.main()

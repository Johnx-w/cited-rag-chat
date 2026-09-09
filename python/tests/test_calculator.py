from __future__ import annotations

import unittest

from src.tools.calculator import calculate


class CalculatorTests(unittest.TestCase):
    def test_mixed_ops(self) -> None:
        self.assertEqual(calculate("(35+17)*4-20"), "188")

    def test_rejects_names(self) -> None:
        with self.assertRaises(ValueError):
            calculate("__import__('os').system('id')")

    def test_rejects_calls(self) -> None:
        with self.assertRaises(ValueError):
            calculate("pow(2, 10)")


if __name__ == "__main__":
    unittest.main()

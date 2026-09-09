from __future__ import annotations

import unittest

from src.agent.fake_client import FakeClient, text_response, tool_response


class FakeClientTests(unittest.TestCase):
    def test_pops_scripted_turns(self) -> None:
        client = FakeClient(
            [
                tool_response("t1", "calculator", {"expression": "1+1"}),
                text_response("done"),
            ]
        )
        first = client.complete(messages=[{"role": "user", "content": "1+1"}])
        self.assertEqual(first.tool_uses[0].name, "calculator")
        second = client.complete(messages=[])
        self.assertEqual(second.text, "done")
        with self.assertRaises(AssertionError):
            client.complete(messages=[])

    def test_records_calls_without_http(self) -> None:
        client = FakeClient([text_response("ok")])
        client.complete(messages=[{"role": "user", "content": "hi"}])
        self.assertEqual(len(client.calls), 1)


if __name__ == "__main__":
    unittest.main()

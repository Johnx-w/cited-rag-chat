from __future__ import annotations

import asyncio
import unittest

from src.mcp_server import mcp
from src.mcp_server import retrieve_knowledge as mcp_retrieve


class McpGateTests(unittest.TestCase):
    def test_only_exposes_retrieve_knowledge(self) -> None:
        tools = asyncio.run(mcp.list_tools())
        names = [tool.name for tool in tools]
        self.assertEqual(names, ["retrieve_knowledge"])

    def test_mcp_tool_goes_through_invoke(self) -> None:
        payload = mcp_retrieve("AlphaCore-7")
        self.assertTrue("result" in payload or "error" in payload or "denied" in payload)
        if "denied" in payload:
            self.fail(payload.get("error"))
        result = payload.get("result") or {}
        self.assertIn("count", result)


if __name__ == "__main__":
    unittest.main()

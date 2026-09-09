import { tool } from "ai";
import { z } from "zod";
import { invokePythonTool } from "./invoke-python";

export const calculator = tool({
  description:
    "计算数学表达式的精确结果。当用户需要四则运算、乘除、括号运算时使用。不要用检索知识库来做算术。",
  execute: async ({ expression }) =>
    await invokePythonTool("calculator", { expression }),
  inputSchema: z.object({
    expression: z.string().describe("算术表达式，例如 (35+17)*4-20"),
  }),
});

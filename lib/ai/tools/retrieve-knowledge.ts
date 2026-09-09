import { tool } from "ai";
import { z } from "zod";
import { invokePythonTool } from "./invoke-python";

export const retrieveKnowledge = tool({
  description:
    "从已导入的内部知识库（Markdown/PDF）检索相关笔记片段。当问题涉及文档中的概念、参数、制度、定义时使用。不要用此工具回答纯算术、当前时间，或「有没有某份文件」这类清单问题。",
  execute: async ({ query, top_k }) => {
    const args: Record<string, string | number | boolean | null> = { query };
    if (typeof top_k === "number") {
      args.top_k = top_k;
    }
    return await invokePythonTool("retrieve_knowledge", args);
  },
  inputSchema: z.object({
    query: z.string().describe("检索用查询词，尽量包含专有名词"),
    top_k: z
      .number()
      .int()
      .min(1)
      .max(20)
      .optional()
      .describe("返回条数，默认使用系统配置 final_k=5"),
  }),
});

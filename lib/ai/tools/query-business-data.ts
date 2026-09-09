import { tool } from "ai";
import { z } from "zod";
import { invokePythonTool } from "./invoke-python";

export function createQueryBusinessData(traceId?: string) {
  return tool({
    description:
      "查询本地演示 SQLite（只读）。表 orders(shipped_on, product, units, revenue_cny) 与 tickets(opened_on, category, status, hours)。只允许单条 SELECT/WITH。这是演示数据，不是知识库笔记，不要写成 [n] 引用。",
    execute: async ({ sql }) =>
      await invokePythonTool("query_business_data", { sql }, traceId),
    inputSchema: z.object({
      sql: z
        .string()
        .describe(
          "只读 SELECT，例如 SELECT product, units FROM orders LIMIT 10"
        ),
    }),
  });
}

export const queryBusinessData = createQueryBusinessData();

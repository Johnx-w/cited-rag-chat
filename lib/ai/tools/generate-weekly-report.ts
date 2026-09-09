import { tool } from "ai";
import { z } from "zod";
import { invokePythonTool } from "./invoke-python";

export function createGenerateWeeklyReport(traceId?: string) {
  return tool({
    description:
      "根据演示 SQLite 生成一周出货/工单摘要。问周报、本周汇总时使用。不要用检索笔记来编造业务数字。week_start 可空，默认本周一。",
    execute: async ({ week_start }) => {
      const args: Record<string, string | number | boolean | null> = {};
      if (week_start) {
        args.week_start = week_start;
      }
      return await invokePythonTool("generate_weekly_report", args, traceId);
    },
    inputSchema: z.object({
      week_start: z
        .string()
        .optional()
        .describe("该周任意一天的 ISO 日期，如 2026-09-01；空则用本周"),
    }),
  });
}

export const generateWeeklyReport = createGenerateWeeklyReport();

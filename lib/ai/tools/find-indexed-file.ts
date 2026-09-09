import { tool } from "ai";
import { z } from "zod";
import { invokePythonTool } from "./invoke-python";

export const findIndexedFile = tool({
  description:
    "按文件名/路径关键字查询「已经导入」的文档清单（元数据目录，不是语义检索）。当用户问「有没有某份文件」「导入了哪些 PDF/Markdown」「文件叫什么」时使用。需要文档内容、定义、参数时请改用 retrieve_knowledge。",
  execute: async ({ name_query }) =>
    await invokePythonTool("find_indexed_file", {
      name_query: name_query ?? "",
    }),
  inputSchema: z.object({
    name_query: z
      .string()
      .optional()
      .describe(
        "文件名或路径子串，如 alphacore、hr_kpi、.pdf；空字符串表示列出全部已导入文档"
      ),
  }),
});

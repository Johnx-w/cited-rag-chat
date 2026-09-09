import { tool } from "ai";
import { z } from "zod";
import { invokePythonTool } from "./invoke-python";

export const getCurrentTime = tool({
  description:
    "获取运行环境的当前本地日期、时间和星期。当用户询问今天几号、星期几、现在几点时使用。",
  execute: async () => await invokePythonTool("get_current_time", {}),
  inputSchema: z.object({}),
});

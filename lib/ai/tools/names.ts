export const chatToolNames = [
  "retrieve_knowledge",
  "calculator",
  "get_current_time",
  "find_indexed_file",
] as const;

export type ChatToolName = (typeof chatToolNames)[number];

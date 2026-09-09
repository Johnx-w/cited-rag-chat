export const chatToolNames = [
  "retrieve_knowledge",
  "calculator",
  "get_current_time",
  "find_indexed_file",
  "query_business_data",
  "generate_weekly_report",
] as const;

export type ChatToolName = (typeof chatToolNames)[number];

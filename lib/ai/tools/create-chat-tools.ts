import { createCalculator } from "./calculator";
import { createFindIndexedFile } from "./find-indexed-file";
import { createGenerateWeeklyReport } from "./generate-weekly-report";
import { createGetCurrentTime } from "./get-current-time";
import { createQueryBusinessData } from "./query-business-data";
import { createRetrieveKnowledge } from "./retrieve-knowledge";

export function createChatTools(traceId?: string) {
  return {
    calculator: createCalculator(traceId),
    find_indexed_file: createFindIndexedFile(traceId),
    generate_weekly_report: createGenerateWeeklyReport(traceId),
    get_current_time: createGetCurrentTime(traceId),
    query_business_data: createQueryBusinessData(traceId),
    retrieve_knowledge: createRetrieveKnowledge(traceId),
  };
}

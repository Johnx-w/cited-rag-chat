import { createCalculator } from "./calculator";
import { createFindIndexedFile } from "./find-indexed-file";
import { createGetCurrentTime } from "./get-current-time";
import { createRetrieveKnowledge } from "./retrieve-knowledge";

export function createChatTools(traceId?: string) {
  return {
    calculator: createCalculator(traceId),
    find_indexed_file: createFindIndexedFile(traceId),
    get_current_time: createGetCurrentTime(traceId),
    retrieve_knowledge: createRetrieveKnowledge(traceId),
  };
}

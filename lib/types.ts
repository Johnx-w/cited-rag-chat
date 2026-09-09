import type { InferUITool, UIMessage } from "ai";
import { z } from "zod";
import type { ArtifactKind } from "@/components/chat/artifact";
import type { calculator } from "./ai/tools/calculator";
import type { findIndexedFile } from "./ai/tools/find-indexed-file";
import type { getCurrentTime } from "./ai/tools/get-current-time";
import type { retrieveKnowledge } from "./ai/tools/retrieve-knowledge";
import type { Suggestion } from "./db/schema";

export const messageMetadataSchema = z.object({
  createdAt: z.string(),
});

export type MessageMetadata = z.infer<typeof messageMetadataSchema>;

type retrieveKnowledgeTool = InferUITool<typeof retrieveKnowledge>;
type calculatorTool = InferUITool<typeof calculator>;
type getCurrentTimeTool = InferUITool<typeof getCurrentTime>;
type findIndexedFileTool = InferUITool<typeof findIndexedFile>;

export type ChatTools = {
  retrieve_knowledge: retrieveKnowledgeTool;
  calculator: calculatorTool;
  get_current_time: getCurrentTimeTool;
  find_indexed_file: findIndexedFileTool;
};

export type WaitingStatusData = {
  phase: "waiting" | "still-waiting" | "health" | "thinking";
  message: string;
  modelId: string;
  modelName: string;
};

export type CustomUIDataTypes = {
  textDelta: string;
  imageDelta: string;
  sheetDelta: string;
  codeDelta: string;
  suggestion: Suggestion;
  appendMessage: string;
  id: string;
  title: string;
  kind: ArtifactKind;
  clear: null;
  finish: null;
  "chat-title": string;
  "waiting-status": WaitingStatusData;
};

export type ChatMessage = UIMessage<
  MessageMetadata,
  CustomUIDataTypes,
  ChatTools
>;

export type Attachment = {
  name: string;
  url: string;
  contentType: string;
};

export const DEFAULT_CHAT_MODEL = "deepseek-chat";

export const titleModel = {
  description: "Fast model for title generation",
  id: "deepseek-chat",
  name: "DeepSeek Chat",
  provider: "deepseek",
};

export type ModelCapabilities = {
  tools: boolean;
  vision: boolean;
  reasoning: boolean;
};

export type ChatModel = {
  id: string;
  name: string;
  provider: string;
  description: string;
  gatewayOrder?: string[];
  reasoningEffort?: "none" | "minimal" | "low" | "medium" | "high";
};

export const chatModels: ChatModel[] = [
  {
    description: "DeepSeek Chat via OpenAI-compatible API, with tool calling",
    id: "deepseek-chat",
    name: "DeepSeek Chat",
    provider: "deepseek",
  },
];

const LOCAL_CAPABILITIES: ModelCapabilities = {
  reasoning: false,
  tools: true,
  vision: false,
};

export function getCapabilities(): Record<string, ModelCapabilities> {
  return Object.fromEntries(
    chatModels.map((model) => [model.id, LOCAL_CAPABILITIES])
  );
}

export const isDemo = process.env.IS_DEMO === "1";

export type GatewayModelWithCapabilities = ChatModel & {
  capabilities: ModelCapabilities;
};

export async function getAllGatewayModels(): Promise<
  GatewayModelWithCapabilities[]
> {
  const capabilities = await getCapabilities();
  return chatModels.map((model) => ({
    ...model,
    capabilities: capabilities[model.id] ?? LOCAL_CAPABILITIES,
  }));
}

export function getActiveModels(): ChatModel[] {
  return chatModels;
}

export const allowedModelIds = new Set(chatModels.map((m) => m.id));

export const modelsByProvider = chatModels.reduce(
  (acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = [];
    }
    acc[model.provider].push(model);
    return acc;
  },
  {} as Record<string, ChatModel[]>
);

export type ModelAvailability = "healthy" | "impacted" | "unknown";

export function getModelAvailability(_modelId: string): ModelAvailability {
  return process.env.DEEPSEEK_API_KEY ? "healthy" : "unknown";
}

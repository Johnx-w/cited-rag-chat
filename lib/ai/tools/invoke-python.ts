import { pythonRagFetch } from "@/lib/rag/python";

type InvokePayload = {
  result?: Record<string, unknown> | string | number | boolean | null;
  error?: string;
  denied?: boolean;
  detail?: unknown;
};

export async function invokePythonTool(
  name: string,
  args: Record<string, string | number | boolean | null>
) {
  try {
    const response = await pythonRagFetch("/tools/invoke", {
      body: JSON.stringify({ arguments: args, name }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });
    const payload = (await response.json()) as InvokePayload;
    if (payload.denied) {
      return {
        denied: true,
        error: payload.error || "Permission denied",
      };
    }
    if (payload.error) {
      return { error: payload.error };
    }
    if (!response.ok) {
      return {
        error:
          typeof payload.detail === "string"
            ? payload.detail
            : `tool failed: ${response.status}`,
      };
    }
    return payload.result ?? { error: "empty tool result" };
  } catch (error) {
    return {
      error: `知识库服务不可用: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

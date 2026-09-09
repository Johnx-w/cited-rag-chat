import { pythonRagFetch } from "@/lib/rag/python";

type StartTracePayload = {
  trace_id?: string;
};

export async function startPythonTrace(
  question: string
): Promise<string | undefined> {
  try {
    const response = await pythonRagFetch("/traces/start", {
      body: JSON.stringify({ question }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });
    if (!response.ok) {
      return;
    }
    const payload = (await response.json()) as StartTracePayload;
    return payload.trace_id;
  } catch {
    /* Python 不可用时跳过 Trace */
  }
}

export async function finishPythonTrace(
  traceId: string,
  answer: string,
  status?: string
): Promise<void> {
  try {
    await pythonRagFetch(`/traces/${traceId}/finish`, {
      body: JSON.stringify({ answer, status }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });
  } catch {
    /* Python 不可用时不能拖死聊天 */
  }
}

type TextPart = {
  type: string;
  text?: string;
};

export function collectMessageText(
  parts: readonly TextPart[] | undefined
): string {
  if (!parts) {
    return "";
  }
  const texts: string[] = [];
  for (const part of parts) {
    if (part.type === "text" && typeof part.text === "string") {
      texts.push(part.text);
    }
  }
  return texts.join("\n").trim();
}

export function lastRoleText(
  messages: ReadonlyArray<{ role: string; parts?: readonly TextPart[] }>,
  role: string
): string {
  let found = "";
  for (const message of messages) {
    if (message.role === role) {
      found = collectMessageText(message.parts);
    }
  }
  return found;
}

import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
} from "@/components/ai-elements/tool";

type ToolState =
  | "input-streaming"
  | "input-available"
  | "output-available"
  | string;

type ChatToolPartProps = {
  part: {
    input?: unknown;
    output?: unknown;
    state: ToolState;
    toolCallId: string;
    type: `tool-${string}`;
  };
};

function asRecord(value: unknown) {
  if (value && typeof value === "object") {
    return value as Record<string, unknown>;
  }
  return null;
}

function toolError(output: unknown) {
  const record = asRecord(output);
  if (record && "error" in record) {
    return String(record.error);
  }
  return null;
}

function footnoteLines(output: unknown) {
  const record = asRecord(output);
  if (!record || !Array.isArray(record.footnotes)) {
    return [];
  }
  return record.footnotes.filter(
    (line): line is string => typeof line === "string"
  );
}

function summary(type: string, output: unknown) {
  const record = asRecord(output);
  if (!record) {
    return "已完成";
  }
  if (type === "tool-retrieve_knowledge") {
    return `命中 ${String(record.count ?? 0)} 条笔记`;
  }
  if (type === "tool-calculator") {
    return `${String(record.expression ?? "")} = ${String(record.value ?? "")}`;
  }
  if (type === "tool-get_current_time") {
    return String(record.text ?? "");
  }
  if (type === "tool-find_indexed_file") {
    return `匹配 ${String(record.match_count ?? 0)} / 已索引 ${String(record.total_indexed ?? 0)}`;
  }
  return "已完成";
}

export function ChatToolPart({ part }: ChatToolPartProps) {
  const { state, type } = part;
  const output = "output" in part ? part.output : undefined;
  const sources = footnoteLines(output);
  const errorText = toolError(output);
  const denied = asRecord(output)?.denied === true;

  return (
    <div className="w-[min(100%,36rem)]">
      <Tool
        className="w-full"
        defaultOpen={state !== "output-available" || denied}
      >
        <ToolHeader state={state} type={type} />
        <ToolContent>
          {(state === "input-available" || state === "input-streaming") &&
          part.input !== undefined ? (
            <ToolInput input={part.input} />
          ) : null}
          {state === "output-available" && errorText ? (
            <div className="px-4 py-3 text-destructive text-sm">
              {errorText}
            </div>
          ) : null}
          {state === "output-available" && !errorText ? (
            <div className="space-y-2 px-4 py-3 text-muted-foreground text-sm">
              <p>{summary(type, output)}</p>
              {sources.length > 0 ? (
                <ul className="list-disc space-y-1 pl-4">
                  {sources.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </ToolContent>
      </Tool>
    </div>
  );
}

export function isChatToolType(
  type: string
): type is
  | "tool-retrieve_knowledge"
  | "tool-calculator"
  | "tool-get_current_time"
  | "tool-find_indexed_file" {
  return (
    type === "tool-retrieve_knowledge" ||
    type === "tool-calculator" ||
    type === "tool-get_current_time" ||
    type === "tool-find_indexed_file"
  );
}

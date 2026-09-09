"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type TraceStep = {
  step_index?: number;
  reasoning_summary?: string;
  action_type?: string;
  action_name?: string;
  action_input?: unknown;
  observation_summary?: string;
  retrieved_refs?: unknown[];
};

type TraceDetail = {
  trace_id?: string;
  question?: string;
  started_at?: string;
  finished_at?: string;
  steps?: TraceStep[];
  final?: { answer?: string; status?: string };
  error?: string;
};

export default function TraceDetailPage() {
  const params = useParams<{ id: string }>();
  const traceId = params.id;
  const [detail, setDetail] = useState<TraceDetail | null>(null);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    const response = await fetch(`/api/traces/${traceId}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(60_000),
    });
    const payload = (await response.json()) as TraceDetail;
    if (!response.ok) {
      setMessage(payload.error || "无法读取 Trace");
      setDetail(null);
      return;
    }
    setDetail(payload);
    setMessage("");
  }, [traceId]);

  useEffect(() => {
    refresh().catch(() => {
      setMessage("知识库服务不可用");
    });
  }, [refresh]);

  const handleRefresh = useCallback(() => {
    refresh().catch(() => {
      setMessage("知识库服务不可用");
    });
  }, [refresh]);

  const steps = detail?.steps ?? [];
  const finalAnswer = detail?.final?.answer || "";

  return (
    <div className="flex h-dvh flex-col bg-background md:rounded-tl-[12px] md:border-t md:border-l md:border-border/40">
      <div className="border-b border-border/40 px-6 py-4">
        <h1 className="text-lg font-semibold tracking-tight">
          Trace {traceId}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {detail?.question || "回放工具调用与最终回答"}
        </p>
      </div>
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
        <div className="flex flex-wrap items-center gap-3">
          <Link className="text-sm underline underline-offset-4" href="/traces">
            返回列表
          </Link>
          <Button onClick={handleRefresh} type="button" variant="ghost">
            刷新
          </Button>
        </div>
        {message ? (
          <p className="text-sm text-muted-foreground">{message}</p>
        ) : null}
        <p className="text-sm text-muted-foreground">
          状态 {detail?.final?.status || "running"}
          {detail?.finished_at ? ` · ${detail.finished_at}` : ""}
        </p>
        <ol className="space-y-3">
          {steps.map((step) => (
            <li
              className="rounded-xl border border-border/50 px-4 py-3 text-sm"
              key={`${step.step_index}-${step.action_name}`}
            >
              <p className="font-medium">
                #{step.step_index} {step.action_type} / {step.action_name}
              </p>
              <p className="mt-1 text-muted-foreground">
                {step.reasoning_summary}
              </p>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-muted-foreground">
                {JSON.stringify(step.action_input, null, 2)}
              </pre>
              <p className="mt-2">{step.observation_summary}</p>
            </li>
          ))}
        </ol>
        {finalAnswer ? (
          <div className="rounded-xl border border-border/50 px-4 py-3 text-sm">
            <p className="font-medium">最终回答</p>
            <p className="mt-2 whitespace-pre-wrap">{finalAnswer}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

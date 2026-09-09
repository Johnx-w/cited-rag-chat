"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type TraceRow = {
  trace_id: string;
  question?: string;
  status?: string;
  finished_at?: string;
};

type TracesResponse = {
  traces?: TraceRow[];
  error?: string;
};

export default function TracesPage() {
  const [rows, setRows] = useState<TraceRow[]>([]);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    const response = await fetch("/api/traces", {
      cache: "no-store",
      signal: AbortSignal.timeout(60_000),
    });
    const payload = (await response.json()) as TracesResponse;
    if (!response.ok) {
      setMessage(payload.error || "无法读取 Trace");
      return;
    }
    setRows(payload.traces ?? []);
    setMessage(`最近 ${payload.traces?.length ?? 0} 条`);
  }, []);

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

  return (
    <div className="flex h-dvh flex-col bg-background md:rounded-tl-[12px] md:border-t md:border-l md:border-border/40">
      <div className="border-b border-border/40 px-6 py-4">
        <h1 className="text-lg font-semibold tracking-tight">Trace 回放</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          聊天和 FakeClient 评测都会写入 JSONL
          Trace。打开一条即可回放工具入参与观察。
        </p>
      </div>
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
        <div className="flex items-center gap-3">
          <Button onClick={handleRefresh} type="button" variant="outline">
            刷新
          </Button>
          <p className="text-sm text-muted-foreground">{message}</p>
        </div>
        <ul className="divide-y divide-border/50 rounded-xl border border-border/50">
          {rows.length === 0 ? (
            <li className="px-4 py-8 text-center text-sm text-muted-foreground">
              还没有 Trace。先去聊天提问，或运行 FakeClient 评测。
            </li>
          ) : (
            rows.map((row) => (
              <li className="px-4 py-3 text-sm" key={row.trace_id}>
                <Link
                  className="flex flex-col gap-1 hover:text-foreground"
                  href={`/traces/${row.trace_id}`}
                >
                  <span className="font-medium">
                    {row.question || row.trace_id}
                  </span>
                  <span className="text-muted-foreground">
                    {row.status || "running"} · {row.trace_id}
                    {row.finished_at ? ` · ${row.finished_at}` : ""}
                  </span>
                </Link>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}

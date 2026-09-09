"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type WeeklyResult = {
  markdown?: string;
  week_start?: string;
  week_end?: string;
  disclaimer?: string;
  error?: string;
};

type WeeklyResponse = {
  result?: WeeklyResult;
  error?: string;
};

export default function ReportsPage() {
  const [markdown, setMarkdown] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      const response = await fetch("/api/reports/weekly", {
        cache: "no-store",
        signal: AbortSignal.timeout(60_000),
      });
      const payload = (await response.json()) as WeeklyResponse;
      if (!response.ok || payload.error) {
        setMessage(payload.error || "无法生成周报");
        return;
      }
      const { result } = payload;
      setMarkdown(result?.markdown || "");
      setMessage(result?.disclaimer || "");
    } finally {
      setBusy(false);
    }
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
        <h1 className="text-lg font-semibold tracking-tight">演示周报</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          数字来自本地只读 SQLite
          演示库，不是生产业务，也不是知识库笔记。聊天里也可以让助手调用
          generate_weekly_report。
        </p>
      </div>
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
        <div className="flex items-center gap-3">
          <Button disabled={busy} onClick={handleRefresh} type="button">
            生成本周演示周报
          </Button>
          <p className="text-sm text-muted-foreground">{message}</p>
        </div>
        <pre className="whitespace-pre-wrap rounded-xl border border-border/50 bg-card/30 px-4 py-4 text-sm">
          {markdown || "还没有周报。"}
        </pre>
      </div>
    </div>
  );
}

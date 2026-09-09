"use client";

import {
  type ChangeEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

type IndexedFile = {
  source: string;
  chunk_count?: number;
  file_type?: string;
};

type FilesResponse = {
  files?: IndexedFile[];
  total_indexed?: number;
  message?: string;
  error?: string;
};

export default function KnowledgePage() {
  const [files, setFiles] = useState<IndexedFile[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    const response = await fetch("/api/knowledge/files", {
      cache: "no-store",
      signal: AbortSignal.timeout(60_000),
    });
    const payload = (await response.json()) as FilesResponse;
    if (!response.ok) {
      setMessage(payload.error || "无法读取知识库");
      return;
    }
    setFiles(payload.files ?? []);
    setMessage(
      payload.message || `已索引 ${payload.total_indexed ?? 0} 个文件`
    );
  }, []);

  useEffect(() => {
    refresh().catch(() => {
      setMessage("知识库服务不可用");
    });
  }, [refresh]);

  const upload = useCallback(
    async (file: File) => {
      setBusy(true);
      try {
        const formData = new FormData();
        formData.set("file", file);
        const response = await fetch("/api/knowledge/upload", {
          body: formData,
          method: "POST",
        });
        const payload = await response.json();
        if (!response.ok || payload.errors?.length) {
          toast.error(payload.error || payload.errors?.[0] || "入库失败");
          return;
        }
        toast.success(`已入库 ${payload.chunks ?? 0} 个片段`);
        await refresh();
      } finally {
        setBusy(false);
      }
    },
    [refresh]
  );

  const ingestSample = useCallback(async () => {
    setBusy(true);
    try {
      const response = await fetch("/api/knowledge/ingest-sample", {
        method: "POST",
      });
      const payload = await response.json();
      if (!response.ok) {
        toast.error(payload.error || "样例入库失败");
        return;
      }
      toast.success(`样例入库 ${payload.chunks ?? 0} 个片段`);
      await refresh();
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  const handleFileChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      event.target.value = "";
      if (!file) {
        return;
      }
      upload(file).catch(() => {
        toast.error("入库失败");
      });
    },
    [upload]
  );

  const handlePickFile = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleIngestSample = useCallback(() => {
    ingestSample().catch(() => {
      toast.error("样例入库失败");
    });
  }, [ingestSample]);

  const handleRefresh = useCallback(() => {
    refresh().catch(() => {
      setMessage("知识库服务不可用");
    });
  }, [refresh]);

  return (
    <div className="flex h-dvh flex-col bg-background md:rounded-tl-[12px] md:border-t md:border-l md:border-border/40">
      <div className="border-b border-border/40 px-6 py-4">
        <h1 className="text-lg font-semibold tracking-tight">知识库</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          上传 Markdown / PDF。切分、向量、BM25 与 RRF 在 Python
          服务里完成；聊天里的 retrieve_knowledge 会按需调用检索。
        </p>
      </div>
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 overflow-y-auto px-6 py-6">
        <div className="flex flex-wrap items-center gap-3">
          <input
            accept=".md,.pdf,text/markdown,application/pdf"
            className="hidden"
            disabled={busy}
            onChange={handleFileChange}
            ref={fileInputRef}
            type="file"
          />
          <Button disabled={busy} onClick={handlePickFile} type="button">
            上传文档
          </Button>
          <Button
            disabled={busy}
            onClick={handleIngestSample}
            type="button"
            variant="outline"
          >
            导入样例语料
          </Button>
          <Button
            disabled={busy}
            onClick={handleRefresh}
            type="button"
            variant="ghost"
          >
            刷新
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">{message}</p>
        <ul className="divide-y divide-border/50 rounded-xl border border-border/50">
          {files.length === 0 ? (
            <li className="px-4 py-8 text-center text-sm text-muted-foreground">
              还没有已索引文档。先上传一篇，或导入样例后再去聊天提问。
            </li>
          ) : (
            files.map((file) => (
              <li
                className="flex items-center justify-between gap-4 px-4 py-3 text-sm"
                key={file.source}
              >
                <span className="min-w-0 truncate">{file.source}</span>
                <span className="shrink-0 text-muted-foreground">
                  {file.chunk_count ?? 0} chunks
                </span>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}

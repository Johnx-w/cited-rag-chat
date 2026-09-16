const MAX_RATE_RETRIES = 3;
const RATE_LIMIT_SLEEP_MS = 500;
const OVERLOAD_SLEEP_MS = 2000;

export function pythonRagUrl() {
  return (
    process.env.PYTHON_RAG_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000"
  );
}

/**
 * 共享密钥。仅当 Python 知识库服务部署在公网（本机不在同一个 Docker 网络里）
 * 时才需要设置；留空则不发这个头，本地开发行为与之前完全一致。
 * 与 Python 侧 python/app/server.py 的 INTERNAL_TOKEN 取同一个值。
 */
function internalToken() {
  return process.env.INTERNAL_TOKEN ?? "";
}

function retryDelayMs(status: number, attempt: number) {
  const base = status === 529 ? OVERLOAD_SLEEP_MS : RATE_LIMIT_SLEEP_MS;
  const jitter = 1 + 0.25 * Math.random();
  return base * 2 ** attempt * jitter;
}

function canRetry(path: string, method: string) {
  if (method === "GET") {
    return true;
  }
  return (
    path === "/retrieve" ||
    path.startsWith("/tools/") ||
    path.startsWith("/traces")
  );
}

function wait(ms: number) {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function fetchOnce(
  path: string,
  init: RequestInit | undefined,
  attempt: number
): Promise<Response> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  const token = internalToken();
  if (token) {
    headers.set("X-Internal-Token", token);
  }
  const response = await fetch(`${pythonRagUrl()}${path}`, {
    cache: "no-store",
    ...init,
    headers,
    signal: init?.signal ?? AbortSignal.timeout(60_000),
  });
  const retryableStatus = response.status === 429 || response.status === 529;
  if (
    !(canRetry(path, method) && retryableStatus && attempt < MAX_RATE_RETRIES)
  ) {
    return response;
  }
  await wait(retryDelayMs(response.status, attempt));
  return fetchOnce(path, init, attempt + 1);
}

export async function pythonRagFetch(
  path: string,
  init?: RequestInit
): Promise<Response> {
  return await fetchOnce(path, init, 0);
}

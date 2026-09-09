const MAX_RATE_RETRIES = 3;
const RATE_LIMIT_SLEEP_MS = 500;
const OVERLOAD_SLEEP_MS = 2000;

export function pythonRagUrl() {
  return (
    process.env.PYTHON_RAG_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000"
  );
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
  return path === "/retrieve" || path.startsWith("/tools/");
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
  const response = await fetch(`${pythonRagUrl()}${path}`, {
    cache: "no-store",
    ...init,
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

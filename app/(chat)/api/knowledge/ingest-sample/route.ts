import { connection, NextResponse } from "next/server";
import { auth } from "@/app/(auth)/auth";
import { pythonRagFetch } from "@/lib/rag/python";

export async function POST() {
  await connection();
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const response = await pythonRagFetch("/ingest-sample", {
      method: "POST",
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        error: `知识库服务不可用: ${error instanceof Error ? error.message : String(error)}`,
      },
      { status: 503 }
    );
  }
}

import { connection, NextResponse } from "next/server";
import { auth } from "@/app/(auth)/auth";
import { pythonRagFetch } from "@/lib/rag/python";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  await connection();
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await context.params;
  try {
    const response = await pythonRagFetch(`/traces/${id}`);
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

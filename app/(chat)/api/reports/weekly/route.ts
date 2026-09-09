import { connection, NextResponse } from "next/server";
import { auth } from "@/app/(auth)/auth";
import { pythonRagFetch } from "@/lib/rag/python";

export async function GET(request: Request) {
  await connection();
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const weekStart = new URL(request.url).searchParams.get("week_start");
  const query = weekStart
    ? `/reports/weekly?week_start=${encodeURIComponent(weekStart)}`
    : "/reports/weekly";

  try {
    const response = await pythonRagFetch(query);
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

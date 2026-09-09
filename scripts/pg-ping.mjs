import { config } from "dotenv";
import postgres from "postgres";

config({ path: ".env.local" });

const sql = postgres(process.env.POSTGRES_URL ?? "", {
  connect_timeout: 5,
  max: 1,
});

try {
  const rows = await sql`select 1 as ok`;
  console.log("query-ok", rows[0].ok);
} catch (error) {
  console.log("query-fail", error.code ?? error.message);
  process.exitCode = 1;
} finally {
  await sql.end({ timeout: 2 });
}

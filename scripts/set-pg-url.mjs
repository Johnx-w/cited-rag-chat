import { execSync } from "node:child_process";
import fs from "node:fs";

const [ip] = execSync('wsl -e bash -lc "hostname -I"', { encoding: "utf8" })
  .trim()
  .split(/\s+/);

if (!ip) {
  throw new Error("Could not read WSL IP");
}

const path = new URL("../.env.local", import.meta.url);
const text = fs.readFileSync(path, "utf8");
const next = text.replace(
  /(POSTGRES_URL=postgres:\/\/cited:)([^@]+)@[^\s]+/,
  `$1$2@${ip}:5433/cited_rag`
);

if (next === text) {
  throw new Error("POSTGRES_URL was not updated");
}

fs.writeFileSync(path, next);
console.log("POSTGRES_URL host/port updated (secret not printed)");

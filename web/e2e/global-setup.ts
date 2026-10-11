import { execSync } from "node:child_process";

export default function globalSetup() {
  // Seed demo data (idempotent) before the servers come up.
  execSync("uv run python -m app.seed.load", {
    cwd: "../backend",
    stdio: "inherit",
  });
}

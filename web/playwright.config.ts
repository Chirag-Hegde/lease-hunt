import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: "http://localhost:3100",
    trace: "retain-on-failure",
  },
  globalSetup: "./e2e/global-setup.ts",
  webServer: [
    {
      command:
        "cd ../backend && uv run uvicorn app.main:app --port 8100",
      url: "http://localhost:8100/api/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run dev -- --port 3100",
      url: "http://localhost:3100",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { NEXT_PUBLIC_API_URL: "http://localhost:8100" },
    },
  ],
});

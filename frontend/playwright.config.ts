import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://localhost:5174",
    headless: true,
    viewport: { width: 1280, height: 800 },
  },
  // Stage 4 T14: backend 假设已由用户手动起（port 8000），frontend npm run dev（port 5174）
  // Playwright 不起 backend；调用方需先保证 backend + frontend 都跑着
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5174",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
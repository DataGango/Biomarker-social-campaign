import { defineConfig } from "@playwright/test";

const python = process.env.PYTHON || "python3";
const port = Number(process.env.DASHBOARD_TEST_PORT || 8765);
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: ".",
  testMatch: "dashboard.spec.mjs",
  reporter: "list",
  timeout: 30_000,
  use: {
    baseURL,
    browserName: "chromium",
    headless: true,
  },
  webServer: {
    command: `${python} ../server.py --port ${port} --skip-initial-refresh`,
    url: `${baseURL}/api/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});

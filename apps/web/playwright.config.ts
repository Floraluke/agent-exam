import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  outputDir: "../../runtime/tests/identity-browser-results",
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "https://127.0.0.1:3100", ignoreHTTPSErrors: true,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: '"../backend/.venv/Scripts/python.exe" -m uvicorn identity.browser_server:app --app-dir ../backend/tests --host 127.0.0.1 --port 8875 --no-access-log',
      url: "http://127.0.0.1:8875/openapi.json",
      reuseExistingServer: false,
      env: { AGENTEXAM_IDENTITY_BROWSER_TEST: "1", PYTHONUTF8: "1" },
    },
    {
      command: "npm run dev -- --port 3100 --experimental-https --experimental-https-key ../../runtime/tests/identity-https-key.pem --experimental-https-cert ../../runtime/tests/identity-https-cert.pem",
      url: "https://127.0.0.1:3100",
      ignoreHTTPSErrors: true,
      reuseExistingServer: false,
      env: { AGENTEXAM_API_ORIGIN: "http://127.0.0.1:8875", NEXT_TELEMETRY_DISABLED: "1" },
    },
  ],
});

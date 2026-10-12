import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { fileURLToPath } from "node:url";
import path from "node:path";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const port = await new Promise((resolve, reject) => {
  const probe = createServer();
  probe.once("error", reject);
  probe.listen(0, "127.0.0.1", () => {
    const address = probe.address();
    probe.close((error) => error ? reject(error) : resolve(address.port));
  });
});

const executable = process.platform === "win32" ? "npx.cmd" : "npx";
const testFile = process.argv[2];
const args = ["playwright", "test", ...(testFile ? [testFile] : [])];
const child = spawn(executable, args, {
  cwd: scriptDirectory,
  stdio: "inherit",
  env: { ...process.env, DASHBOARD_TEST_PORT: String(port) },
});

child.on("error", (error) => {
  console.error(`Could not start Playwright: ${error.message}`);
  process.exitCode = 1;
});
child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exitCode = code ?? 1;
  }
});

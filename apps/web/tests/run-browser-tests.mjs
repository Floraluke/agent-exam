// Each spec gets fresh synthetic backend state and the unchanged login budget.
import { readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const directory = dirname(fileURLToPath(import.meta.url));
const root = dirname(directory);
const selected = process.argv.slice(2);
const files = readdirSync(directory).filter((file) =>
  file.endsWith(".spec.ts") && (selected.length === 0 || selected.includes(file)),
).sort();
if (files.length === 0 || selected.some((file) => !files.includes(file))) {
  throw new Error("Specify existing .spec.ts basenames, or omit arguments to run all.");
}
for (const file of files) {
  const result = spawnSync(process.execPath, [
    join(root, "node_modules", "@playwright", "test", "cli.js"), "test", file,
    "--output", join(root, "..", "..", "runtime", "tests", "identity-browser-results", file),
  ], { cwd: root, stdio: "inherit", env: process.env });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

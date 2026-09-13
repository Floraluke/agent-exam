// Each spec gets fresh synthetic backend state and the unchanged login budget.
import { readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const directory = dirname(fileURLToPath(import.meta.url));
const root = dirname(directory);
const selected = process.argv.slice(2);
const discovered = readdirSync(directory, { recursive: true })
  .map((file) => String(file).replaceAll("\\", "/"))
  .filter((file) => file.endsWith(".spec.ts"))
  .sort();
const files = discovered.filter((file) => selected.length === 0 ||
  selected.includes(file) || selected.includes(file.split("/").at(-1)));
if (files.length === 0 || selected.some((name) =>
  !files.includes(name) && !files.some((file) => file.endsWith("/" + name)))) {
  throw new Error("Specify existing .spec.ts paths or unique basenames, or omit arguments.");
}
for (const file of files) {
  const result = spawnSync(process.execPath, [
    join(root, "node_modules", "@playwright", "test", "cli.js"), "test", file,
    "--output", join(root, "..", "..", "runtime", "tests",
      "identity-browser-results", file.replaceAll("/", "__")),
  ], { cwd: root, stdio: "inherit", env: process.env });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

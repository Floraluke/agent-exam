// Each spec gets fresh synthetic backend state and the unchanged login budget.
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
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
// Next updates these generated references for a custom distDir. Preserve the
// tracked clean-clone defaults even when a browser test fails.
const generatedReferences = ["next-env.d.ts", "tsconfig.json"].map((name) => {
  const path = join(root, name);
  return { path, content: readFileSync(path) };
});
let exitCode = 0;
try {
  for (const file of files) {
    const result = spawnSync(process.execPath, [
      join(root, "node_modules", "@playwright", "test", "cli.js"), "test", file,
      "--output", join(root, "..", "..", "runtime", "tests",
        "identity-browser-results", file.replaceAll("/", "__")),
    ], { cwd: root, stdio: "inherit", env: process.env });
    if (result.error) throw result.error;
    if (result.status !== 0) {
      exitCode = result.status ?? 1;
      break;
    }
  }
} finally {
  for (const reference of generatedReferences) {
    writeFileSync(reference.path, reference.content);
  }
}
if (exitCode !== 0) process.exit(exitCode);

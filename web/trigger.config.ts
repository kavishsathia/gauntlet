import { defineConfig } from "@trigger.dev/sdk/v3";
import { pythonExtension } from "@trigger.dev/python/extension";

export default defineConfig({
  project: "proj_udzairppurpmxygxzsos",
  runtime: "node",
  logLevel: "log",
  maxDuration: 300,
  retries: {
    enabledInDev: false,
    default: { maxAttempts: 1 },
  },
  dirs: ["./src/trigger"],
  build: {
    extensions: [
      pythonExtension({
        requirementsFile: "./requirements.txt",
        scripts: ["./python"],
      }),
    ],
  },
});

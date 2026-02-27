import { task } from "@trigger.dev/sdk/v3";
import { python } from "@trigger.dev/python";

export const runDemoTask = task({
  id: "run-demo",
  maxDuration: 300,
  run: async (payload: { runId: string; hypothesis?: string }) => {
    const result = await python.runScript("./python/run_demo.py", [], {
      env: {
        ...process.env,
        RUN_ID: payload.runId,
        HYPOTHESIS: payload.hypothesis || "",
      } as Record<string, string>,
    });

    return { stdout: result.stdout, stderr: result.stderr };
  },
});

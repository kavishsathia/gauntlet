import { NextResponse } from "next/server";
import { tasks } from "@trigger.dev/sdk/v3";
import type { runDemoTask } from "@/src/trigger/run-demo";

export async function POST(req: Request) {
  try {
    const { runId, hypothesis } = await req.json();

    if (!runId) {
      return NextResponse.json({ error: "runId is required" }, { status: 400 });
    }

    const handle = await tasks.trigger<typeof runDemoTask>("run-demo", {
      runId,
      hypothesis: hypothesis || "",
    });

    return NextResponse.json({ runId, taskId: handle.id, status: "started" });
  } catch (err) {
    return NextResponse.json(
      { error: `Internal error: ${err}` },
      { status: 500 }
    );
  }
}

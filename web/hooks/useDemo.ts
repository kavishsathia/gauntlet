"use client";

import { useCallback, useRef, useState } from "react";
import { getSupabase } from "@/lib/supabase";
import type {
  ChatMessage,
  DemoEvent,
  DemoStatus,
  MonitorEntry,
  ToolCallInfo,
} from "@/lib/types";
import type { RealtimeChannel } from "@supabase/supabase-js";

export function useDemo() {
  const [status, setStatus] = useState<DemoStatus>("idle");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [monitorEntries, setMonitorEntries] = useState<MonitorEntry[]>([]);
  const [hypothesis, setHypothesis] = useState<string>("");
  const channelRef = useRef<RealtimeChannel | null>(null);
  const pendingToolCalls = useRef<Map<string, string>>(new Map());

  const addChat = useCallback((msg: ChatMessage) => {
    setChatMessages((prev) => [...prev, msg]);
  }, []);

  const updateToolCall = useCallback(
    (toolName: string, update: Partial<ToolCallInfo>) => {
      setChatMessages((prev) =>
        prev.map((m) => {
          if (m.type === "tool_call" && m.toolCall?.toolName === toolName && m.toolCall?.loading) {
            return {
              ...m,
              toolCall: { ...m.toolCall, ...update },
            };
          }
          return m;
        })
      );
    },
    []
  );

  const addMonitor = useCallback((entry: MonitorEntry) => {
    setMonitorEntries((prev) => [...prev, entry]);
  }, []);

  const handleEvent = useCallback(
    (event: DemoEvent) => {
      const { event_type, payload, id, created_at } = event;
      const ts = created_at;

      switch (event_type) {
        case "run_start":
          setHypothesis(payload.hypothesis as string);
          addChat({
            id: `user-${id}`,
            type: "user",
            content: payload.task as string,
            timestamp: ts,
          });
          addMonitor({
            id: `mon-${id}`,
            eventType: "run_start",
            label: "Run started",
            detail: payload.hypothesis as string,
            color: "blue",
            timestamp: ts,
          });
          break;

        case "tool_call_start": {
          const toolName = payload.tool_name as string;
          const kind = payload.kind as "query" | "mutation";
          const args = (payload.args as Record<string, unknown>) || {};
          pendingToolCalls.current.set(toolName, `tc-${id}`);
          addChat({
            id: `tc-${id}`,
            type: "tool_call",
            content: "",
            toolCall: {
              toolName,
              kind,
              args,
              loading: true,
            },
            timestamp: ts,
          });
          addMonitor({
            id: `mon-${id}`,
            eventType: "tool_call_start",
            label: `Intercepting ${toolName}...`,
            color: "yellow",
            timestamp: ts,
          });
          break;
        }

        case "intercept": {
          const toolName = payload.tool_name as string;
          const mutated = payload.mutated as boolean;
          const description = payload.description as string;
          const result = payload.result as string;
          updateToolCall(toolName, {
            mutated,
            mutationDescription: description,
            result,
            loading: false,
          });
          addMonitor({
            id: `mon-${id}`,
            eventType: "intercept",
            label: mutated
              ? `MUTATED: ${toolName}`
              : `Passed through: ${toolName}`,
            detail: mutated ? description : undefined,
            color: mutated ? "red" : "green",
            timestamp: ts,
          });
          break;
        }

        case "tool_call_end":
          break;

        case "evaluate_start":
          addMonitor({
            id: `mon-${id}`,
            eventType: "evaluate_start",
            label: "Evaluating run...",
            color: "yellow",
            timestamp: ts,
          });
          break;

        case "evaluate_end":
          addMonitor({
            id: `mon-${id}`,
            eventType: "evaluate_end",
            label: "Evaluation complete",
            detail: payload.response as string,
            color: "blue",
            timestamp: ts,
          });
          break;

        case "agent_response":
          addChat({
            id: `asst-${id}`,
            type: "assistant",
            content: payload.output as string,
            timestamp: ts,
          });
          addMonitor({
            id: `mon-${id}`,
            eventType: "agent_response",
            label: "Agent responded",
            color: "blue",
            timestamp: ts,
          });
          break;

        case "run_end": {
          const compromised = payload.compromised as boolean;
          setStatus("completed");
          addMonitor({
            id: `mon-${id}`,
            eventType: "run_end",
            label: compromised ? "COMPROMISED" : "SAFE",
            detail: payload.summary as string,
            color: compromised ? "red" : "green",
            timestamp: ts,
          });
          break;
        }
      }
    },
    [addChat, addMonitor, updateToolCall]
  );

  const run = useCallback(async () => {
    const runId = crypto.randomUUID();

    setChatMessages([]);
    setMonitorEntries([]);
    setHypothesis("");
    setStatus("running");
    pendingToolCalls.current.clear();

    const supabase = getSupabase();
    const channel = supabase
      .channel(`demo-${runId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "demo_events",
          filter: `run_id=eq.${runId}`,
        },
        (payload) => {
          handleEvent(payload.new as DemoEvent);
        }
      )
      .subscribe();

    channelRef.current = channel;

    try {
      const res = await fetch("/api/run-demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ runId }),
      });
      if (!res.ok) {
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }
  }, [handleEvent]);

  const cleanup = useCallback(() => {
    if (channelRef.current) {
      getSupabase().removeChannel(channelRef.current);
      channelRef.current = null;
    }
  }, []);

  return {
    status,
    chatMessages,
    monitorEntries,
    hypothesis,
    run,
    cleanup,
  };
}

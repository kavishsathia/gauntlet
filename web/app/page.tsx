"use client";

import { useEffect } from "react";
import { useDemo } from "@/hooks/useDemo";
import { RunButton } from "@/components/RunButton";
import { ChatPanel } from "@/components/ChatPanel";
import { GauntletMonitor } from "@/components/GauntletMonitor";

export default function Home() {
  const { status, chatMessages, monitorEntries, hypothesis, run, cleanup } =
    useDemo();

  useEffect(() => {
    return () => cleanup();
  }, [cleanup]);

  return (
    <div className="h-screen flex flex-col noise-bg">
      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold tracking-tight">
            <span className="text-red-500">Gauntlet</span>
          </h1>
          <span className="text-xs text-white/30 hidden sm:inline">
            Adversarial fuzz-testing for AI agents
          </span>
        </div>

        <RunButton status={status} onClick={run} />
      </header>

      {/* Main content */}
      <main className="relative z-10 flex-1 flex overflow-hidden">
        {/* Chat panel — left 60% */}
        <div className="w-[60%] border-r border-white/[0.06] bg-white/[0.01]">
          <ChatPanel messages={chatMessages} />
        </div>

        {/* Gauntlet monitor — right 40% */}
        <div className="w-[40%] bg-black/20">
          <GauntletMonitor entries={monitorEntries} hypothesis={hypothesis} />
        </div>
      </main>

      {/* Status bar */}
      <footer className="relative z-10 px-6 py-2 border-t border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={`w-1.5 h-1.5 rounded-full ${
              status === "idle"
                ? "bg-white/20"
                : status === "running"
                ? "bg-yellow-500 animate-pulse"
                : status === "completed"
                ? "bg-emerald-500"
                : "bg-red-500"
            }`}
          />
          <span className="text-[11px] text-white/30">
            {status === "idle" && "Ready"}
            {status === "running" && "Agent under test..."}
            {status === "completed" && "Run complete"}
            {status === "error" && "Error occurred"}
          </span>
        </div>
        <span className="text-[11px] text-white/20">
          Powered by Elasticsearch Agent Builder
        </span>
      </footer>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { useDemo } from "@/hooks/useDemo";
import { RunButton } from "@/components/RunButton";
import { ChatPanel } from "@/components/ChatPanel";
import { GauntletMonitor } from "@/components/GauntletMonitor";
import { HypothesisPicker } from "@/components/HypothesisPicker";

export default function Home() {
  const { status, chatMessages, monitorEntries, hypothesis, run, cleanup } =
    useDemo();
  const [selectedHypothesis, setSelectedHypothesis] = useState("");

  useEffect(() => {
    return () => cleanup();
  }, [cleanup]);

  const handleRun = () => run(selectedHypothesis);

  return (
    <div className="h-screen flex flex-col noise-bg">
      <header className="relative z-10 flex flex-col gap-4 px-8 py-5 border-b border-white/[0.04]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-5">
            <Image
              src="/logo.png"
              alt="Gauntlet"
              width={140}
              height={32}
              className="opacity-90"
              priority
            />
            <div className="h-4 w-px bg-white/[0.08]" />
            <span className="text-[11px] text-white/25 tracking-wide hidden sm:inline">
              Adversarial fuzz-testing for AI agents
            </span>
          </div>

          <RunButton status={status} onClick={handleRun} />
        </div>

        <HypothesisPicker
          value={selectedHypothesis}
          onChange={setSelectedHypothesis}
          disabled={status === "running"}
        />
      </header>

      <main className="relative z-10 flex-1 flex overflow-hidden">
        <div className="w-[58%] border-r border-white/[0.04]">
          <ChatPanel messages={chatMessages} />
        </div>

        <div className="w-[42%]">
          <GauntletMonitor entries={monitorEntries} hypothesis={hypothesis} />
        </div>
      </main>

      <footer className="relative z-10 px-8 py-2.5 border-t border-white/[0.04] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${
              status === "idle"
                ? "bg-white/15"
                : status === "running"
                ? "bg-amber-400/80 animate-pulse"
                : status === "completed"
                ? "bg-emerald-400/80"
                : "bg-red-400/80"
            }`}
          />
          <span className="text-[11px] text-white/25 tracking-wide">
            {status === "idle" && "Ready"}
            {status === "running" && "Agent under test..."}
            {status === "completed" && "Run complete"}
            {status === "error" && "Error occurred"}
          </span>
        </div>
        <span className="text-[11px] text-white/15 tracking-wide">
          Powered by Elasticsearch Agent Builder
        </span>
      </footer>
    </div>
  );
}

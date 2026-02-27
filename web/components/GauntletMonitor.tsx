"use client";

import { useEffect, useRef } from "react";
import type { MonitorEntry } from "@/lib/types";

interface GauntletMonitorProps {
  entries: MonitorEntry[];
  hypothesis: string;
}

const colorMap = {
  blue: { dot: "bg-blue-400/60", text: "text-blue-400/80" },
  yellow: { dot: "bg-amber-400/60 animate-pulse", text: "text-amber-400/80" },
  green: { dot: "bg-emerald-400/60", text: "text-emerald-400/80" },
  red: { dot: "bg-red-400/70", text: "text-red-400/80" },
};

export function GauntletMonitor({ entries, hypothesis }: GauntletMonitorProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <div className="flex flex-col h-full bg-black/10">
      <div className="px-6 py-4 border-b border-white/[0.04]">
        <h2 className="text-xs font-medium text-white/30 uppercase tracking-[0.15em]">
          Monitor
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {hypothesis && (
          <div className="mb-6 rounded-lg bg-white/[0.02] border border-white/[0.04] p-4">
            <p className="text-[9px] uppercase tracking-[0.15em] text-white/20 mb-2">Hypothesis</p>
            <p className="text-[12px] text-white/50 leading-relaxed">{hypothesis}</p>
          </div>
        )}

        {entries.length === 0 && !hypothesis && (
          <div className="flex items-center justify-center h-full">
            <p className="text-white/15 text-sm">Waiting for events...</p>
          </div>
        )}

        <div className="space-y-0">
          {entries.map((entry, i) => {
            const colors = colorMap[entry.color];
            const isLast = i === entries.length - 1;
            const isRunEnd = entry.eventType === "run_end";
            const isCompromised = isRunEnd && entry.label === "COMPROMISED";

            return (
              <div key={entry.id} className="flex gap-3.5 animate-fade-in">
                <div className="flex flex-col items-center">
                  <div
                    className={`
                      ${isRunEnd ? "w-3 h-3" : "w-2 h-2"} rounded-full shrink-0 mt-1.5
                      ${colors.dot}
                      ${isCompromised ? "shadow-[0_0_8px_rgba(248,113,113,0.4)]" : ""}
                    `}
                  />
                  {!isLast && (
                    <div className="w-px flex-1 min-h-[20px] bg-white/[0.04]" />
                  )}
                </div>

                <div className="pb-4">
                  <p className={`text-[12px] font-medium ${colors.text}`}>
                    {entry.label}
                  </p>
                  {entry.detail && (
                    <p className="text-[11px] text-white/35 mt-0.5 leading-relaxed">
                      {entry.detail}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div ref={bottomRef} />
      </div>
    </div>
  );
}

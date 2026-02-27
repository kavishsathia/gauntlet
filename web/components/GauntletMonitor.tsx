"use client";

import { useEffect, useRef } from "react";
import type { MonitorEntry } from "@/lib/types";

interface GauntletMonitorProps {
  entries: MonitorEntry[];
  hypothesis: string;
}

const colorMap = {
  blue: { dot: "bg-blue-500", line: "border-blue-500/30", text: "text-blue-400" },
  yellow: { dot: "bg-yellow-500 animate-pulse", line: "border-yellow-500/30", text: "text-yellow-400" },
  green: { dot: "bg-emerald-500", line: "border-emerald-500/30", text: "text-emerald-400" },
  red: { dot: "bg-red-500", line: "border-red-500/30", text: "text-red-400" },
};

export function GauntletMonitor({ entries, hypothesis }: GauntletMonitorProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-4 border-b border-white/5">
        <h2 className="text-sm font-semibold text-red-400/80 uppercase tracking-wider">
          Gauntlet Monitor
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {hypothesis && (
          <div className="mb-6 rounded-lg bg-white/[0.03] border border-white/[0.06] p-4">
            <p className="text-[10px] uppercase tracking-wider text-white/30 mb-2">Hypothesis</p>
            <p className="text-xs text-white/60 leading-relaxed">{hypothesis}</p>
          </div>
        )}

        {entries.length === 0 && !hypothesis && (
          <div className="flex items-center justify-center h-full">
            <p className="text-white/20 text-sm">Waiting for events...</p>
          </div>
        )}

        <div className="space-y-0">
          {entries.map((entry, i) => {
            const colors = colorMap[entry.color];
            const isLast = i === entries.length - 1;
            const isRunEnd = entry.eventType === "run_end";

            return (
              <div key={entry.id} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div
                    className={`
                      ${isRunEnd ? "w-4 h-4" : "w-2.5 h-2.5"} rounded-full flex-shrink-0 mt-1
                      ${colors.dot}
                      ${isRunEnd ? "shadow-[0_0_12px_rgba(239,68,68,0.5)]" : ""}
                    `}
                  />
                  {!isLast && (
                    <div className="w-px flex-1 min-h-[24px] bg-white/[0.06]" />
                  )}
                </div>

                <div className={`pb-4 ${isLast ? "" : ""}`}>
                  <p className={`text-xs font-medium ${colors.text}`}>
                    {entry.label}
                  </p>
                  {entry.detail && (
                    <p className="text-[11px] text-white/40 mt-0.5 leading-relaxed">
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

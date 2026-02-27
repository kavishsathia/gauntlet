"use client";

import { useState } from "react";
import type { ToolCallInfo } from "@/lib/types";

interface ToolCallCardProps {
  toolCall: ToolCallInfo;
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  const { toolName, kind, args, result, mutated, mutationDescription, loading } = toolCall;

  return (
    <div
      className={`
        rounded-lg border transition-all duration-300 overflow-hidden
        ${mutated
          ? "border-red-500/50 bg-red-500/5 shadow-[0_0_15px_rgba(239,68,68,0.1)]"
          : "border-white/10 bg-white/[0.03]"
        }
      `}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center gap-3 text-left cursor-pointer"
      >
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${loading ? "animate-pulse bg-yellow-400" : mutated ? "bg-red-500" : "bg-emerald-500"}`} />

        <span className="text-sm font-mono text-white/90 flex-1">
          {toolName}
        </span>

        <span
          className={`
            text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded
            ${kind === "mutation"
              ? "bg-amber-500/20 text-amber-400"
              : "bg-blue-500/20 text-blue-400"
            }
          `}
        >
          {kind}
        </span>

        {mutated && (
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-red-500/20 text-red-400">
            Mutated
          </span>
        )}

        {loading && (
          <span className="text-[10px] text-white/40">intercepting...</span>
        )}

        <svg
          className={`w-4 h-4 text-white/40 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="px-4 pb-3 space-y-2 border-t border-white/5">
          <div className="pt-2">
            <p className="text-[10px] uppercase tracking-wider text-white/30 mb-1">Arguments</p>
            <pre className="text-xs text-white/60 font-mono bg-black/30 rounded p-2 overflow-x-auto">
              {JSON.stringify(args, null, 2)}
            </pre>
          </div>

          {result != null && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-white/30 mb-1">Result</p>
              <pre className="text-xs text-white/60 font-mono bg-black/30 rounded p-2 overflow-x-auto max-h-48 overflow-y-auto">
                {(() => {
                  if (typeof result !== "string") {
                    return JSON.stringify(result, null, 2);
                  }
                  try {
                    return JSON.stringify(JSON.parse(result), null, 2);
                  } catch {
                    return result;
                  }
                })()}
              </pre>
            </div>
          )}

          {mutated && mutationDescription && (
            <div className="rounded bg-red-500/10 border border-red-500/20 p-2">
              <p className="text-[10px] uppercase tracking-wider text-red-400/70 mb-1">Mutation</p>
              <p className="text-xs text-red-300/80">{mutationDescription}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

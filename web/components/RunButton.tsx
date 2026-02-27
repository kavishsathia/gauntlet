"use client";

import type { DemoStatus } from "@/lib/types";

interface RunButtonProps {
  status: DemoStatus;
  onClick: () => void;
}

export function RunButton({ status, onClick }: RunButtonProps) {
  const isRunning = status === "running";

  return (
    <button
      onClick={onClick}
      disabled={isRunning}
      className={`
        relative px-8 py-3 rounded-lg font-semibold text-sm tracking-wide uppercase
        transition-all duration-300 cursor-pointer
        ${
          isRunning
            ? "bg-red-500/20 text-red-400 border border-red-500/30"
            : "bg-red-600 text-white hover:bg-red-500 hover:shadow-lg hover:shadow-red-500/25 active:scale-95"
        }
        disabled:cursor-not-allowed
      `}
    >
      {isRunning && (
        <span className="absolute inset-0 rounded-lg animate-pulse bg-red-500/10" />
      )}
      <span className="relative flex items-center gap-2">
        {isRunning && (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        )}
        {status === "idle" && "Run the Gauntlet"}
        {status === "running" && "Running..."}
        {status === "completed" && "Run Again"}
        {status === "error" && "Retry"}
      </span>
    </button>
  );
}

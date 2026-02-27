"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/types";
import { ToolCallCard } from "./ToolCallCard";

interface ChatPanelProps {
  messages: ChatMessage[];
}

export function ChatPanel({ messages }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-4 border-b border-white/5">
        <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Agent Chat
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="text-white/20 text-sm">
              Click &quot;Run the Gauntlet&quot; to start
            </p>
          </div>
        )}

        {messages.map((msg) => {
          if (msg.type === "user") {
            return (
              <div key={msg.id} className="flex justify-end">
                <div className="max-w-[80%] bg-white/10 rounded-2xl rounded-br-md px-4 py-2.5">
                  <p className="text-sm text-white/90">{msg.content}</p>
                </div>
              </div>
            );
          }

          if (msg.type === "tool_call" && msg.toolCall) {
            return (
              <div key={msg.id} className="mx-2">
                <ToolCallCard toolCall={msg.toolCall} />
              </div>
            );
          }

          if (msg.type === "assistant") {
            return (
              <div key={msg.id} className="flex justify-start">
                <div className="max-w-[80%] bg-white/[0.04] border border-white/[0.06] rounded-2xl rounded-bl-md px-4 py-2.5">
                  <p className="text-sm text-white/80 whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            );
          }

          return null;
        })}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}

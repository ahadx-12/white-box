"use client";

import { useState } from "react";
import type { ChatMessage, VerificationResponse, VerifyOptions } from "@/lib/types";
import { fetchJob, verifyAsync, verifySync } from "@/lib/api";
import { generateRequestId, sleep } from "@/lib/utils";
import MessageBubble from "@/components/MessageBubble";

export default function ChatPanel({
  onProofSelect,
  selectedPack,
  mode,
  options,
  debugEnabled,
  onStatusChange,
}: {
  onProofSelect: (proof?: VerificationResponse) => void;
  selectedPack: string;
  mode: "sync" | "async";
  options?: VerifyOptions;
  debugEnabled: boolean;
  onStatusChange: (status: "idle" | "verifying" | "verified" | "failed") => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  const updateMessage = (id: string, patch: Partial<ChatMessage>) => {
    setMessages((prev) =>
      prev.map((message) => (message.id === id ? { ...message, ...patch } : message)),
    );
  };

  const handleProof = (proof?: VerificationResponse) => {
    onProofSelect(proof);
  };

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isSending) return;
    setIsSending(true);
    setInput("");

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
      mode,
    };

    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: mode === "async" ? "Queued async verification…" : "Running verification…",
      status: mode === "async" ? "queued" : "running",
      mode,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    onStatusChange("verifying");

    try {
      const requestId = generateRequestId();
      if (mode === "sync") {
        const result = await verifySync(
          trimmed,
          selectedPack,
          requestId,
          options,
          debugEnabled,
        );
        updateMessage(assistantMessage.id, {
          content: result.final_answer ?? "No answer returned.",
          status: result.status,
          proof: result,
        });
        handleProof(result);
        onStatusChange(result.status === "verified" ? "verified" : "failed");
      } else {
        const asyncResult = await verifyAsync(
          trimmed,
          selectedPack,
          requestId,
          options,
          debugEnabled,
        );
        updateMessage(assistantMessage.id, {
          content: `Job queued (${asyncResult.job_id}). Waiting…`,
          status: asyncResult.status,
          jobId: asyncResult.job_id,
        });
        const jobResult = await pollJob(asyncResult.job_id);
        if (jobResult?.result) {
          updateMessage(assistantMessage.id, {
            content: jobResult.result.final_answer ?? "No answer returned.",
            status: jobResult.result.status,
            proof: jobResult.result,
          });
          handleProof(jobResult.result);
          onStatusChange(jobResult.result.status === "verified" ? "verified" : "failed");
        } else if (jobResult?.status) {
          updateMessage(assistantMessage.id, {
            status: jobResult.status,
            content: jobResult.error
              ? `Job failed: ${jobResult.error}`
              : `Job status: ${jobResult.status}`,
          });
          onStatusChange(jobResult.status === "failed" ? "failed" : "idle");
        }
      }
    } catch (error) {
      updateMessage(assistantMessage.id, {
        status: "error",
        content: error instanceof Error ? error.message : "Request failed.",
      });
      onStatusChange("failed");
    } finally {
      setIsSending(false);
    }
  };

  const pollJob = async (jobId: string) => {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const job = await fetchJob(jobId);
      if (job.status === "done" || job.status === "failed") {
        return job;
      }
      await sleep(1000);
    }
    return fetchJob(jobId);
  };

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex-1 space-y-3 overflow-y-auto" data-testid="chat-messages">
        {messages.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-700 p-6 text-sm text-slate-400">
            Start the conversation by asking a question.
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <label className="text-xs uppercase text-slate-400">Message</label>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          rows={3}
          className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950 p-3 text-sm text-slate-100"
          placeholder="Ask a question to verify"
          data-testid="chat-input"
        />
        <div className="mt-3 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Pack: {selectedPack} • Mode: {mode} • Debug: {debugEnabled ? "on" : "off"}
          </span>
          <button
            type="button"
            onClick={handleSend}
            disabled={isSending}
            className="rounded-md bg-indigo-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            data-testid="send-button"
          >
            {isSending ? "Sending…" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

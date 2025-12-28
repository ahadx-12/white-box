"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  ChatMessage,
  VerificationResponse,
  VerifyOptions,
} from "@/lib/types";
import { fetchJob, fetchPacks, verifyAsync, verifySync } from "@/lib/api";
import { generateRequestId, sleep } from "@/lib/utils";
import MessageBubble from "@/components/MessageBubble";
import ModeToggle from "@/components/ModeToggle";
import PackSelector from "@/components/PackSelector";

const DEFAULT_PACK = "general";

export default function ChatPanel({
  onProofSelect,
}: {
  onProofSelect: (proof?: VerificationResponse) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [packs, setPacks] = useState<string[]>([DEFAULT_PACK]);
  const [selectedPack, setSelectedPack] = useState(DEFAULT_PACK);
  const [mode, setMode] = useState<"sync" | "async">("sync");
  const [maxIters, setMaxIters] = useState<string>("");
  const [threshold, setThreshold] = useState<string>("");
  const [isSending, setIsSending] = useState(false);

  const options: VerifyOptions | undefined = useMemo(() => {
    const parsedMax = Number(maxIters);
    const parsedThreshold = Number(threshold);
    const payload: VerifyOptions = {};
    if (maxIters.trim() && !Number.isNaN(parsedMax) && parsedMax > 0) {
      payload.max_iters = parsedMax;
    }
    if (threshold.trim() && !Number.isNaN(parsedThreshold) && parsedThreshold >= 0) {
      payload.threshold = parsedThreshold;
    }
    return Object.keys(payload).length ? payload : undefined;
  }, [maxIters, threshold]);

  useEffect(() => {
    const loadPacks = async () => {
      try {
        const response = await fetchPacks();
        if (response.packs.length) {
          setPacks(response.packs);
          setSelectedPack((current) =>
            response.packs.includes(current) ? current : response.packs[0],
          );
        }
      } catch {
        // Keep default pack if API is unavailable.
      }
    };
    loadPacks();
  }, []);

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

    try {
      const requestId = generateRequestId();
      if (mode === "sync") {
        const result = await verifySync(trimmed, selectedPack, requestId, options);
        updateMessage(assistantMessage.id, {
          content: result.final_answer ?? "No answer returned.",
          status: result.status,
          proof: result,
        });
        handleProof(result);
      } else {
        const asyncResult = await verifyAsync(trimmed, selectedPack, requestId, options);
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
        } else if (jobResult?.status) {
          updateMessage(assistantMessage.id, {
            status: jobResult.status,
            content: jobResult.error
              ? `Job failed: ${jobResult.error}`
              : `Job status: ${jobResult.status}`,
          });
        }
      }
    } catch (error) {
      updateMessage(assistantMessage.id, {
        status: "error",
        content: error instanceof Error ? error.message : "Request failed.",
      });
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
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <PackSelector
          packs={packs}
          selected={selectedPack}
          onChange={setSelectedPack}
        />
        <ModeToggle mode={mode} onToggle={setMode} />
        <div className="flex flex-col gap-1 text-sm">
          <label className="text-xs uppercase text-slate-400">Max iters</label>
          <input
            value={maxIters}
            onChange={(event) => setMaxIters(event.target.value)}
            placeholder="default"
            className="w-24 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1 text-sm">
          <label className="text-xs uppercase text-slate-400">Threshold</label>
          <input
            value={threshold}
            onChange={(event) => setThreshold(event.target.value)}
            placeholder="default"
            className="w-24 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          />
        </div>
      </div>

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
            Pack: {selectedPack} • Mode: {mode}
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

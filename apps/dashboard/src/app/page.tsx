"use client";

import { useEffect, useMemo, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import ControlBar from "@/components/ControlBar";
import ProofPanel from "@/components/ProofPanel";
import ThreeBackground from "@/components/ThreeBackground";
import { fetchHealth, fetchPacks } from "@/lib/api";
import type { VerificationResponse, VerifyOptions } from "@/lib/types";

export default function Page() {
  const [activeProof, setActiveProof] = useState<VerificationResponse | undefined>(
    undefined,
  );
  const [packs, setPacks] = useState<string[]>(["general"]);
  const [selectedPack, setSelectedPack] = useState("general");
  const [mode, setMode] = useState<"sync" | "async">("sync");
  const [debugEnabled, setDebugEnabled] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [maxIters, setMaxIters] = useState<string>("");
  const [threshold, setThreshold] = useState<string>("");
  const [status, setStatus] = useState<"idle" | "verifying" | "verified" | "failed">(
    "idle",
  );
  const [apiStatus, setApiStatus] = useState<"checking" | "up" | "down">("checking");

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
        // Keep defaults if API is unavailable.
      }
    };
    loadPacks();
  }, []);

  useEffect(() => {
    let active = true;
    const checkHealth = async () => {
      try {
        await fetchHealth();
        if (active) {
          setApiStatus("up");
        }
      } catch {
        if (active) {
          setApiStatus("down");
        }
      }
    };
    checkHealth();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-950 p-6 text-slate-100">
      <ThreeBackground status={status} reducedMotion={reduceMotion} />
      <header className="mb-6 space-y-2">
        <h1 className="text-2xl font-semibold text-white">
          TrustAI Verification Dashboard
        </h1>
        <p className="text-sm text-slate-400">
          Track convergence, visualize proof artifacts, and debug verification loops
          in real time.
        </p>
        <div className="flex items-center gap-2 text-xs text-slate-300">
          <span
            className={`h-2 w-2 rounded-full ${
              apiStatus === "up"
                ? "bg-emerald-400"
                : apiStatus === "down"
                  ? "bg-rose-400"
                  : "bg-amber-400"
            }`}
            aria-hidden="true"
          />
          <span>
            API status:{" "}
            {apiStatus === "checking"
              ? "Checking..."
              : apiStatus === "up"
                ? "Online"
                : "Offline"}
          </span>
        </div>
      </header>

      <div className="space-y-6">
        <ControlBar
          packs={packs}
          selectedPack={selectedPack}
          onPackChange={setSelectedPack}
          mode={mode}
          onModeChange={setMode}
          debugEnabled={debugEnabled}
          onDebugChange={setDebugEnabled}
          reduceMotion={reduceMotion}
          onReduceMotionChange={setReduceMotion}
          maxIters={maxIters}
          onMaxItersChange={setMaxIters}
          threshold={threshold}
          onThresholdChange={setThreshold}
        />

        <div className="grid h-[calc(100vh-220px)] gap-6 lg:grid-cols-[2fr_1fr]">
          <section className="flex h-full flex-col" aria-label="chat panel">
            <ChatPanel
              onProofSelect={setActiveProof}
              selectedPack={selectedPack}
              mode={mode}
              options={options}
              debugEnabled={debugEnabled}
              onStatusChange={setStatus}
            />
          </section>
          <aside
            className="h-full rounded-2xl border border-slate-800 bg-slate-900/40 p-5 backdrop-blur"
            aria-label="proof panel"
          >
            <ProofPanel proof={activeProof} />
          </aside>
        </div>
      </div>
    </main>
  );
}

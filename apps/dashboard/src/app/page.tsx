"use client";

import { useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import ProofPanel from "@/components/ProofPanel";
import type { VerificationResponse } from "@/lib/types";

export default function Page() {
  const [activeProof, setActiveProof] = useState<VerificationResponse | undefined>(
    undefined,
  );

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <header className="mb-6 space-y-2">
        <h1 className="text-2xl font-semibold text-white">
          TrustAI Verification Dashboard
        </h1>
        <p className="text-sm text-slate-400">
          Chat with the verifier, inspect proof artifacts, and monitor iteration
          quality in real time.
        </p>
      </header>

      <div className="grid h-[calc(100vh-160px)] gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="flex h-full flex-col" aria-label="chat panel">
          <ChatPanel onProofSelect={setActiveProof} />
        </section>
        <aside
          className="h-full rounded-xl border border-slate-800 bg-slate-900/40 p-5"
          aria-label="proof panel"
        >
          <ProofPanel proof={activeProof} />
        </aside>
      </div>
    </main>
  );
}

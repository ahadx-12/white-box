import type { VerificationResponse } from "@/lib/types";
import { formatScore } from "@/lib/utils";
import IterationTimeline from "@/components/IterationTimeline";

const ListSection = ({ title, items }: { title: string; items: string[] }) => (
  <div>
    <h4 className="text-xs uppercase tracking-wide text-slate-400">{title}</h4>
    {items.length ? (
      <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-slate-200">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    ) : (
      <p className="mt-2 text-sm text-slate-500">None.</p>
    )}
  </div>
);

export default function ProofPanel({ proof }: { proof?: VerificationResponse }) {
  if (!proof) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        No proof selected yet.
      </div>
    );
  }

  const finalScore =
    proof.similarity_history[proof.similarity_history.length - 1] ?? 0;

  return (
    <div className="flex h-full flex-col gap-6 overflow-y-auto" data-testid="proof-panel">
      <header className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Proof Overview</h2>
          <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-200">
            {proof.status}
          </span>
        </div>
        <div className="text-xs text-slate-400">Proof ID: {proof.proof_id}</div>
        <div className="flex flex-wrap gap-3 text-xs text-slate-300">
          <span>Pack: {proof.pack}</span>
          <span>Fingerprint: {proof.pack_fingerprint}</span>
          <span>Final Score: {formatScore(finalScore)}</span>
        </div>
      </header>

      <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-200">
        <h3 className="text-xs uppercase text-slate-400">Summary</h3>
        <p className="mt-2 leading-relaxed" data-testid="proof-summary">
          {proof.explain.summary}
        </p>
      </section>

      <section className="grid gap-4">
        <ListSection title="Key Conflicts" items={proof.explain.key_conflicts} />
        <ListSection
          title="Unsupported Claims"
          items={proof.explain.unsupported_claims}
        />
        <ListSection
          title="Missing Evidence"
          items={proof.explain.missing_evidence}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-xs uppercase text-slate-400">Iterations</h3>
        <IterationTimeline iterations={proof.iterations} />
      </section>
    </div>
  );
}

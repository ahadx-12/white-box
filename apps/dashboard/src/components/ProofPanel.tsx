import { useMemo, useState } from "react";
import type { IterationSummary, VerificationResponse } from "@/lib/types";
import { formatScore } from "@/lib/utils";
import GraphView from "@/components/GraphView";
import IterationTimeline from "@/components/IterationTimeline";

const tabs = ["summary", "timeline", "graph", "diff", "json"] as const;
type TabKey = (typeof tabs)[number];

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

const parseFeedback = (feedback: string) => {
  const sections = {
    remove: [] as string[],
    add: [] as string[],
    forbid: [] as string[],
  };
  let current: "remove" | "add" | "forbid" | null = null;
  feedback.split("\n").forEach((line) => {
    if (line.startsWith("MUST REMOVE:")) current = "remove";
    else if (line.startsWith("MUST ADD:")) current = "add";
    else if (line.startsWith("MUST NOT CLAIM:")) current = "forbid";
    else if (line.startsWith("- ") && current) {
      sections[current].push(line.replace("- ", ""));
    }
  });
  return sections;
};

export default function ProofPanel({ proof }: { proof?: VerificationResponse }) {
  const [activeTab, setActiveTab] = useState<TabKey>("summary");
  const [selectedIteration, setSelectedIteration] = useState<number | undefined>(
    undefined,
  );
  const iterationDetails = useMemo(() => {
    if (!proof || proof.iterations.length === 0) {
      return undefined;
    }
    return (
      proof.iterations.find((item) => item.i === selectedIteration) ??
      proof.iterations[proof.iterations.length - 1]
    );
  }, [proof, selectedIteration]);
  const feedbackSections = useMemo(
    () => parseFeedback(iterationDetails?.feedback_text ?? ""),
    [iterationDetails?.feedback_text],
  );

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
    <div className="flex h-full flex-col gap-4 overflow-y-auto" data-testid="proof-panel">
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

      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`rounded-full px-3 py-1 text-xs uppercase tracking-wide transition ${
              activeTab === tab
                ? "bg-indigo-500 text-white"
                : "border border-slate-800 text-slate-300 hover:border-slate-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "summary" ? (
        <div className="space-y-4">
          <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-200">
            <h3 className="text-xs uppercase text-slate-400">Summary</h3>
            <p className="mt-2 leading-relaxed" data-testid="proof-summary">
              {proof.explain.summary}
            </p>
          </section>
          <section className="grid gap-4">
            <ListSection
              title="Key Conflicts"
              items={proof.explain.key_conflicts}
            />
            <ListSection
              title="Unsupported Claims"
              items={proof.explain.unsupported_claims}
            />
            <ListSection
              title="Missing Required"
              items={proof.explain.missing_required}
            />
          </section>
        </div>
      ) : null}

      {activeTab === "timeline" ? (
        <section className="space-y-4">
          <IterationTimeline
            iterations={proof.iterations}
            selected={iterationDetails?.i}
            onSelect={(iteration) => setSelectedIteration(iteration.i)}
          />
          {iterationDetails ? (
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
              <h3 className="text-xs uppercase text-slate-400">Iteration details</h3>
              <p className="mt-2 text-slate-400">
                Answer delta: {iterationDetails.answer_delta_summary}
              </p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <ListSection
                  title="Top conflicts"
                  items={iterationDetails.top_conflicts}
                />
                <ListSection
                  title="Feedback"
                  items={
                    iterationDetails.feedback_text
                      ? iterationDetails.feedback_text.split("\n")
                      : []
                  }
                />
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      {activeTab === "graph" ? (
        <GraphView iteration={iterationDetails} />
      ) : null}

      {activeTab === "diff" ? (
        <section className="space-y-4 text-sm text-slate-200">
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
            <h3 className="text-xs uppercase text-slate-400">Answer delta</h3>
            <p className="mt-2">{iterationDetails?.answer_delta_summary}</p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <ListSection title="Must add" items={feedbackSections.add} />
            <ListSection title="Must remove" items={feedbackSections.remove} />
            <ListSection title="Must not claim" items={feedbackSections.forbid} />
          </div>
        </section>
      ) : null}

      {activeTab === "json" ? (
        <section className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-xs text-slate-300">
          <pre className="whitespace-pre-wrap break-words">
            {JSON.stringify(proof, null, 2)}
          </pre>
        </section>
      ) : null}
    </div>
  );
}

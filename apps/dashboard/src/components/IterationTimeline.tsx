import type { IterationSummary } from "@/lib/types";
import { formatScore } from "@/lib/utils";

export default function IterationTimeline({
  iterations,
  selected,
  onSelect,
}: {
  iterations: IterationSummary[];
  selected?: number;
  onSelect?: (iteration: IterationSummary) => void;
}) {
  if (!iterations.length) {
    return <p className="text-sm text-slate-400">No iterations yet.</p>;
  }

  return (
    <ol className="space-y-2">
      {iterations.map((iteration) => (
        <li
          key={iteration.i}
          className={`rounded-md border p-3 transition ${
            selected === iteration.i
              ? "border-indigo-400/60 bg-indigo-900/40"
              : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
          }`}
          onClick={() => onSelect?.(iteration)}
          role={onSelect ? "button" : undefined}
        >
          <div className="flex items-center justify-between text-xs uppercase text-slate-400">
            <span>Iteration {iteration.i}</span>
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] ${
                iteration.accepted
                  ? "bg-emerald-600/30 text-emerald-300"
                  : "bg-rose-600/30 text-rose-300"
              }`}
            >
              {iteration.accepted ? "Accepted" : "Rejected"}
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between text-sm">
            <span className="text-slate-300">Score</span>
            <span className="font-semibold text-slate-100">
              {formatScore(iteration.score)}
            </span>
          </div>
          {iteration.rejected_because.length ? (
            <div className="mt-2 text-xs text-slate-400">
              <span className="uppercase">Reasons:</span> {" "}
              {iteration.rejected_because.join(", ")}
            </div>
          ) : null}
        </li>
      ))}
    </ol>
  );
}

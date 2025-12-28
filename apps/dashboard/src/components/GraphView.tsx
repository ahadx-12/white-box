"use client";

import { useMemo, useState } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import type { IterationSummary } from "@/lib/types";

import "reactflow/dist/style.css";

const filters = ["all", "conflicts", "missing"] as const;

type FilterKey = (typeof filters)[number];

const buildGraph = (
  iteration: IterationSummary | undefined,
  filter: FilterKey,
) => {
  const nodes: Node[] = [
    {
      id: "answer",
      position: { x: 0, y: 0 },
      data: { label: "Answer" },
      className: "rounded-lg border border-slate-700 bg-slate-900 text-slate-100 px-3 py-2",
    },
  ];
  const edges: Edge[] = [];
  if (!iteration) {
    return { nodes, edges };
  }

  const items: { id: string; label: string; kind: "conflict" | "missing" | "unsupported" }[] = [];
  const conflicts = iteration.conflicts ?? [];
  const missing = iteration.missing ?? [];
  const unsupported = iteration.unsupported ?? [];

  if (filter !== "missing") {
    conflicts.forEach((item, idx) => {
      items.push({ id: `conflict-${idx}`, label: item, kind: "conflict" });
    });
    unsupported.forEach((item, idx) => {
      items.push({ id: `unsupported-${idx}`, label: item, kind: "unsupported" });
    });
  }
  if (filter !== "conflicts") {
    missing.forEach((item, idx) => {
      items.push({ id: `missing-${idx}`, label: item, kind: "missing" });
    });
  }

  const baseX = 260;
  const baseY = -120;
  items.forEach((item, index) => {
    const y = baseY + index * 80;
    nodes.push({
      id: item.id,
      position: { x: baseX, y },
      data: { label: item.label },
      className: `rounded-lg border px-3 py-2 text-xs ${
        item.kind === "missing"
          ? "border-amber-400/60 bg-amber-500/10 text-amber-100"
          : "border-rose-500/60 bg-rose-500/10 text-rose-100"
      }`,
    });
    edges.push({
      id: `edge-${item.id}`,
      source: "answer",
      target: item.id,
      label: item.kind,
      animated: item.kind !== "missing",
    });
  });

  return { nodes, edges };
};

export default function GraphView({
  iteration,
}: {
  iteration?: IterationSummary;
}) {
  const [activeFilter, setActiveFilter] = useState<FilterKey>("all");
  const graph = useMemo(
    () => buildGraph(iteration, activeFilter),
    [iteration, activeFilter],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {filters.map((filter) => (
          <button
            key={filter}
            type="button"
            onClick={() => setActiveFilter(filter)}
            className={`rounded-full px-3 py-1 text-xs uppercase tracking-wide transition ${
              activeFilter === filter
                ? "bg-indigo-500 text-white"
                : "border border-slate-800 text-slate-300 hover:border-slate-700"
            }`}
          >
            {filter}
          </button>
        ))}
      </div>
      <div className="h-[320px] rounded-lg border border-slate-800 bg-slate-950">
        <ReactFlow
          nodes={graph.nodes}
          edges={graph.edges}
          fitView
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#1f2937" gap={24} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}

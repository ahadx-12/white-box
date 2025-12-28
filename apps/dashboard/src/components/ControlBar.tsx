"use client";

import PackSelector from "@/components/PackSelector";
import ModeToggle from "@/components/ModeToggle";

export default function ControlBar({
  packs,
  selectedPack,
  onPackChange,
  mode,
  onModeChange,
  debugEnabled,
  onDebugChange,
  reduceMotion,
  onReduceMotionChange,
  maxIters,
  onMaxItersChange,
  threshold,
  onThresholdChange,
}: {
  packs: string[];
  selectedPack: string;
  onPackChange: (value: string) => void;
  mode: "sync" | "async";
  onModeChange: (mode: "sync" | "async") => void;
  debugEnabled: boolean;
  onDebugChange: (value: boolean) => void;
  reduceMotion: boolean;
  onReduceMotionChange: (value: boolean) => void;
  maxIters: string;
  onMaxItersChange: (value: string) => void;
  threshold: string;
  onThresholdChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur">
      <PackSelector packs={packs} selected={selectedPack} onChange={onPackChange} />
      <ModeToggle mode={mode} onToggle={onModeChange} />
      <div className="flex flex-col gap-1 text-sm">
        <label className="text-xs uppercase text-slate-400">Debug</label>
        <button
          type="button"
          onClick={() => onDebugChange(!debugEnabled)}
          className={`rounded-full px-3 py-2 text-xs uppercase tracking-wide transition ${
            debugEnabled
              ? "bg-emerald-500/20 text-emerald-200"
              : "border border-slate-700 text-slate-300"
          }`}
          data-testid="debug-toggle"
        >
          {debugEnabled ? "On" : "Off"}
        </button>
      </div>
      <div className="flex flex-col gap-1 text-sm">
        <label className="text-xs uppercase text-slate-400">Reduce motion</label>
        <button
          type="button"
          onClick={() => onReduceMotionChange(!reduceMotion)}
          className={`rounded-full px-3 py-2 text-xs uppercase tracking-wide transition ${
            reduceMotion
              ? "bg-slate-700 text-slate-200"
              : "border border-slate-700 text-slate-300"
          }`}
        >
          {reduceMotion ? "On" : "Off"}
        </button>
      </div>
      <div className="flex flex-col gap-1 text-sm">
        <label className="text-xs uppercase text-slate-400">Max iters</label>
        <input
          value={maxIters}
          onChange={(event) => onMaxItersChange(event.target.value)}
          placeholder="default"
          className="w-24 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
        />
      </div>
      <div className="flex flex-col gap-1 text-sm">
        <label className="text-xs uppercase text-slate-400">Threshold</label>
        <input
          value={threshold}
          onChange={(event) => onThresholdChange(event.target.value)}
          placeholder="default"
          className="w-24 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
        />
      </div>
    </div>
  );
}

export default function ModeToggle({
  mode,
  onToggle,
}: {
  mode: "sync" | "async";
  onToggle: (mode: "sync" | "async") => void;
}) {
  return (
    <div className="flex flex-col gap-2 text-sm">
      <span className="text-xs uppercase text-slate-400">Mode</span>
      <div className="flex gap-2 rounded-full bg-slate-800 p-1">
        {(["sync", "async"] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => onToggle(option)}
            className={`rounded-full px-3 py-1 text-xs uppercase tracking-wide transition ${
              mode === option
                ? "bg-indigo-500 text-white"
                : "text-slate-300 hover:text-white"
            }`}
            data-testid={`mode-${option}`}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}

import type { ChangeEvent } from "react";

export default function PackSelector({
  packs,
  selected,
  onChange,
}: {
  packs: string[];
  selected: string;
  onChange: (value: string) => void;
}) {
  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onChange(event.target.value);
  };

  return (
    <div className="flex flex-col gap-1 text-sm">
      <label className="text-xs uppercase text-slate-400">Pack</label>
      <select
        value={selected}
        onChange={handleChange}
        className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
        data-testid="pack-selector"
      >
        {packs.map((pack) => (
          <option key={pack} value={pack}>
            {pack}
          </option>
        ))}
      </select>
    </div>
  );
}

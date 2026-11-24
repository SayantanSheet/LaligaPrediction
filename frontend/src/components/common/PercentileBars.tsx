import type { MetricKey } from "@/api/types";

export const METRIC_LABELS: Record<MetricKey, string> = {
  goals: "Goals", assists: "Assists", shots: "Shots", shots_on: "Shots on target", key_passes: "Key passes", passes: "Passes",
  pass_accuracy: "Pass accuracy", dribbles_won: "Successful dribbles", tackles: "Tackles", interceptions: "Interceptions",
  duels_won: "Duels won", fouls_drawn: "Fouls drawn", rating: "Average rating",
};
const PER90: MetricKey[] = ["goals", "assists", "shots", "shots_on", "key_passes", "passes", "dribbles_won", "tackles", "interceptions", "duels_won", "fouls_drawn"];

/** Percentile vs. position peers. Ordinal ramp: the bar fill steps darker with the percentile. */
export function PercentileBars({ percentiles, per90 }: { percentiles: Record<MetricKey, number | null>; per90: Record<MetricKey, number | null> }) {
  const keys = Object.keys(METRIC_LABELS) as MetricKey[];
  return (
    <ul className="space-y-2.5">
      {keys.map((k) => {
        const p = percentiles[k];
        if (p === null || p === undefined) return null;
        const v = per90[k];
        return (
          <li key={k} className="grid grid-cols-[minmax(0,9rem)_1fr_3.5rem] items-center gap-3 text-sm">
            <span className="truncate text-muted-foreground">{METRIC_LABELS[k]}</span>
            <div className="h-2 rounded-full" style={{ background: "color-mix(in srgb, var(--series-home) 15%, transparent)" }}>
              <div className="h-full rounded-full" style={{ width: `${Math.max(2, p)}%`, background: p >= 80 ? "var(--seq-700)" : p >= 50 ? "var(--seq-500)" : "var(--seq-300)" }} />
            </div>
            <span className="text-right tabular">
              <span className="font-semibold">{Math.round(p)}</span>
              <span className="ml-1 text-[10px] text-muted-foreground">{v !== null && v !== undefined ? (PER90.includes(k) ? v.toFixed(2) : v.toFixed(k === "rating" ? 2 : 0)) : ""}</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

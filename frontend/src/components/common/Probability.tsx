import { cn } from "@/lib/utils";
import { pct } from "@/lib/format";

/**
 * One whole split into home / draw / away. Segments are separated by a 2px surface gap (no strokes);
 * the legend under the bar carries identity with text in ink colours.
 */
export function ProbabilityBar({ home, draw, away, homeLabel = "Home", awayLabel = "Away", height = "h-3", showLegend = true, className }: {
  home: number; draw: number; away: number; homeLabel?: string; awayLabel?: string; height?: string; showLegend?: boolean; className?: string;
}) {
  const total = home + draw + away || 1;
  const seg = [
    { key: "home", v: home, color: "var(--series-home)", label: homeLabel },
    { key: "draw", v: draw, color: "var(--series-draw)", label: "Draw" },
    { key: "away", v: away, color: "var(--series-away)", label: awayLabel },
  ];
  return (
    <div className={className}>
      <div className={cn("flex w-full gap-[2px] overflow-hidden rounded-full", height)} role="img"
        aria-label={`${homeLabel} ${pct(home)}, draw ${pct(draw)}, ${awayLabel} ${pct(away)}`}>
        {seg.map((s) => (
          <div key={s.key} style={{ width: `${(s.v / total) * 100}%`, background: s.color }} className="h-full transition-[width] duration-700 first:rounded-l-full last:rounded-r-full" />
        ))}
      </div>
      {showLegend && (
        <div className="mt-2 flex justify-between gap-2 text-xs">
          {seg.map((s, i) => (
            <span key={s.key} className={cn("flex min-w-0 items-center gap-1.5", i === 1 && "justify-center", i === 2 && "justify-end")}>
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: s.color }} aria-hidden />
              <span className="truncate text-muted-foreground">{s.label}</span>
              <span className="font-semibold tabular">{pct(s.v)}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** Single probability meter: filled track on a lighter track of the same hue. */
export function Meter({ label, value, sublabel, color = "var(--series-home)", className }: { label: string; value: number; sublabel?: string; color?: string; className?: string }) {
  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between gap-2 text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold tabular">
          {pct(value)}
          {sublabel && <span className="ml-1.5 text-xs font-normal text-muted-foreground">{sublabel}</span>}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full" style={{ background: `color-mix(in srgb, ${color} 18%, transparent)` }}>
        <div className="h-full rounded-full transition-[width] duration-700" style={{ width: `${Math.min(100, value)}%`, background: color }} />
      </div>
    </div>
  );
}

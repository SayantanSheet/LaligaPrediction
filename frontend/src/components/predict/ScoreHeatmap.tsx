import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { pct } from "@/lib/format";

/** Sequential single-hue heatmap of P(home goals = row, away goals = col). */
export function ScoreHeatmap({ matrix, home, away, highlight }: { matrix: number[][]; home: string; away: string; highlight?: string }) {
  const max = Math.max(...matrix.flat());
  const n = matrix.length;
  return (
    <div className="overflow-x-auto">
      <div className="inline-block min-w-full">
        <div className="mb-2 text-center text-xs text-muted-foreground">{away} goals →</div>
        <div className="flex">
          <div className="flex w-6 items-center justify-center">
            <span className="-rotate-90 whitespace-nowrap text-xs text-muted-foreground">{home} goals →</span>
          </div>
          <div className="grid flex-1 gap-[2px]" style={{ gridTemplateColumns: `1.5rem repeat(${n}, minmax(2.75rem, 1fr))` }} role="table" aria-label="Scoreline probability matrix">
            <div />
            {matrix[0].map((_, j) => (
              <div key={j} className="pb-1 text-center text-xs font-medium text-muted-foreground tabular">{j === n - 1 ? `${j}` : j}</div>
            ))}
            {matrix.map((row, i) => (
              <div key={i} className="contents" role="row">
                <div className="flex items-center justify-center text-xs font-medium text-muted-foreground tabular">{i}</div>
                {row.map((v, j) => {
                  const t = max ? v / max : 0;
                  const dark = t > 0.55;
                  const isPick = highlight === `${i}-${j}`;
                  return (
                    <Tooltip key={j}>
                      <TooltipTrigger asChild>
                        <div
                          role="cell"
                          tabIndex={0}
                          className="flex h-11 items-center justify-center rounded-[4px] text-[11px] font-medium tabular outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          style={{
                            background: `color-mix(in srgb, var(--seq-700) ${Math.round(t * 100)}%, var(--seq-100))`,
                            color: dark ? "var(--heat-ink-high)" : "var(--heat-ink-low)",
                            boxShadow: isPick ? "inset 0 0 0 2px hsl(var(--foreground))" : undefined,
                          }}
                        >
                          {v >= 1 ? v.toFixed(0) : v >= 0.1 ? v.toFixed(1) : ""}
                        </div>
                      </TooltipTrigger>
                      <TooltipContent className="text-xs">
                        {home} {i} – {j} {away}: <span className="font-semibold">{pct(v)}</span>
                      </TooltipContent>
                    </Tooltip>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
        <p className="mt-2 text-center text-[11px] text-muted-foreground">Cell values are probabilities in %. Stronger colour = more likely. Outlined cell = most likely score.</p>
      </div>
    </div>
  );
}

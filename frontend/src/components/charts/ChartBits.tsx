import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Shared Recharts props so every chart has the same recessive grid/axes. */
export const axisProps = {
  stroke: "var(--chart-grid)",
  tick: { fill: "var(--chart-axis)", fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: "var(--chart-grid)" },
} as const;

export const gridProps = { stroke: "var(--chart-grid)", strokeDasharray: "0", vertical: false } as const;

export function Legend({ items, className }: { items: { label: ReactNode; color: string; dashed?: boolean }[]; className?: string }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground", className)}>
      {items.map((it, i) => (
        <span key={i} className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: it.color }} aria-hidden />
          {it.label}
        </span>
      ))}
    </div>
  );
}

type TooltipPayload = { name?: string; value?: number | string; color?: string; dataKey?: string | number; payload?: Record<string, unknown> };

/** Tooltip for Recharts: series swatch beside ink-coloured text. */
export function ChartTooltip({ active, payload, label, formatter, labelFormatter }: {
  active?: boolean; payload?: TooltipPayload[]; label?: ReactNode;
  formatter?: (v: number | string, name: string, p: TooltipPayload) => ReactNode; labelFormatter?: (l: ReactNode, p?: TooltipPayload[]) => ReactNode;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-lg">
      {label !== undefined && label !== "" && <div className="mb-1 font-medium">{labelFormatter ? labelFormatter(label, payload) : label}</div>}
      <div className="space-y-0.5">
        {payload.map((p, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ background: p.color }} aria-hidden />
            <span className="text-muted-foreground">{p.name}</span>
            <span className="ml-auto pl-3 font-semibold tabular">{formatter ? formatter(p.value ?? "", String(p.name), p) : p.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

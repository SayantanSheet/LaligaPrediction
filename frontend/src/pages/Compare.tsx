import { useSearchParams, Link } from "react-router-dom";
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip as RTooltip } from "recharts";
import { ArrowLeftRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel } from "@/components/common/Panel";
import { PlayerAvatar } from "@/components/common/Crest";
import { PlayerPicker } from "@/components/common/Pickers";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { ChartTooltip, Legend } from "@/components/charts/ChartBits";
import { useCompare } from "@/hooks/queries";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { PlayerProfile } from "@/api/types";

function Header({ p, side }: { p: PlayerProfile; side: "a" | "b" }) {
  return (
    <Link to={`/players/${p.id}`} className={cn("flex items-center gap-3", side === "b" && "flex-row-reverse text-right")}>
      <span className="relative">
        <PlayerAvatar name={p.name} photo={p.photo} size="lg" />
        <span className="absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full border-2 border-card" style={{ background: side === "a" ? "var(--series-home)" : "var(--series-away)" }} aria-hidden />
      </span>
      <span className="min-w-0">
        <span className="block truncate font-semibold hover:underline">{p.name}</span>
        <span className="block truncate text-xs text-muted-foreground">{p.team} · {p.position} · {num(p.minutes)} min</span>
      </span>
    </Link>
  );
}

export default function Compare() {
  const [params, setParams] = useSearchParams();
  const a = params.get("a") ? Number(params.get("a")) : null;
  const b = params.get("b") ? Number(params.get("b")) : null;
  const set = (k: "a" | "b", v: number | null) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, String(v)); else next.delete(k);
    setParams(next, { replace: true });
  };
  const { data, isLoading, error, refetch } = useCompare(a ?? undefined, b ?? undefined);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Players" title="Player comparison"
        description="Side-by-side per-90 output and percentile ranks against position peers. Share the URL to share the comparison." />
      <section className="grid items-center gap-3 rounded-2xl border bg-card p-4 shadow-sm md:grid-cols-[1fr_auto_1fr]">
        <PlayerPicker label="Player A" value={a} onChange={(v) => set("a", v)} exclude={b} />
        <Button variant="ghost" size="icon" className="mx-auto" aria-label="Swap players" onClick={() => { const n = new URLSearchParams(); if (b) n.set("a", String(b)); if (a) n.set("b", String(a)); setParams(n, { replace: true }); }}>
          <ArrowLeftRight className="h-4 w-4" />
        </Button>
        <PlayerPicker label="Player B" value={b} onChange={(v) => set("b", v)} exclude={a} />
      </section>

      {!a || !b ? <EmptyState title="Choose two players to compare" className="py-16">Tip: open any player profile and press “Compare”.</EmptyState>
        : isLoading ? <LoadingBlock rows={8} />
          : error || !data ? <ErrorState error={error} onRetry={refetch} />
            : (
              <>
                <Panel>
                  <div className="grid items-center gap-4 md:grid-cols-[1fr_auto_1fr]">
                    <Header p={data.a} side="a" />
                    <div className="text-center">
                      <div className="font-mono text-3xl font-semibold tabular">{data.edge.a} – {data.edge.b}</div>
                      <div className="text-[11px] text-muted-foreground">metrics won</div>
                    </div>
                    <Header p={data.b} side="b" />
                  </div>
                </Panel>
                <div className="grid gap-6 lg:grid-cols-5">
                  <Panel title="Percentile radar" subtitle="Per-90 percentile vs. position peers (450+ min)" className="lg:col-span-2">
                    <Legend className="mb-2" items={[{ label: data.a.name, color: "var(--series-home)" }, { label: data.b.name, color: "var(--series-away)" }]} />
                    <div className="h-80">
                      <ResponsiveContainer>
                        <RadarChart data={data.radar} outerRadius="72%">
                          <PolarGrid stroke="var(--chart-grid)" />
                          <PolarAngleAxis dataKey="metric" tick={{ fill: "var(--chart-axis)", fontSize: 10 }} />
                          <RTooltip content={<ChartTooltip formatter={(v) => `${Math.round(Number(v))}th pct`} />} />
                          <Radar name={data.a.name} dataKey="a" stroke="var(--series-home)" fill="var(--series-home)" fillOpacity={0.12} strokeWidth={2} />
                          <Radar name={data.b.name} dataKey="b" stroke="var(--series-away)" fill="var(--series-away)" fillOpacity={0.12} strokeWidth={2} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </Panel>
                  <Panel title="Head-to-head stats" subtitle="Per 90 minutes unless stated · season totals in grey" className="lg:col-span-3" bodyClassName="px-2 pb-3 pt-2">
                    <table className="w-full text-sm">
                      <thead className="text-xs text-muted-foreground">
                        <tr>
                          <th className="px-2 py-1.5 text-right font-medium">{data.a.name}</th>
                          <th className="px-2 py-1.5 text-center font-medium">Metric</th>
                          <th className="px-2 py-1.5 text-left font-medium">{data.b.name}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.rows.map((r) => {
                          const max = Math.max(r.a ?? 0, r.b ?? 0) || 1;
                          return (
                            <tr key={r.key} className="border-t">
                              <td className="px-2 py-2">
                                <div className="flex items-center justify-end gap-2">
                                  <span className="text-[10px] text-muted-foreground tabular">{r.key !== "rating" && r.key !== "pass_accuracy" ? r.a_total : ""}</span>
                                  <span className={cn("tabular", r.better === "a" ? "font-bold" : "text-muted-foreground")}>{r.a?.toFixed(2) ?? "—"}</span>
                                  <div className="hidden h-1.5 w-20 justify-end rounded-full bg-muted sm:flex"><div className="h-full rounded-full" style={{ width: `${((r.a ?? 0) / max) * 100}%`, background: "var(--series-home)" }} /></div>
                                </div>
                              </td>
                              <td className="px-2 py-2 text-center text-xs text-muted-foreground">{r.label}</td>
                              <td className="px-2 py-2">
                                <div className="flex items-center gap-2">
                                  <div className="hidden h-1.5 w-20 rounded-full bg-muted sm:block"><div className="h-full rounded-full" style={{ width: `${((r.b ?? 0) / max) * 100}%`, background: "var(--series-away)" }} /></div>
                                  <span className={cn("tabular", r.better === "b" ? "font-bold" : "text-muted-foreground")}>{r.b?.toFixed(2) ?? "—"}</span>
                                  <span className="text-[10px] text-muted-foreground tabular">{r.key !== "rating" && r.key !== "pass_accuracy" ? r.b_total : ""}</span>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </Panel>
                </div>
              </>
            )}
    </div>
  );
}

import { CartesianGrid, Bar, BarChart, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ComposedChart, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { Link } from "react-router-dom";
import { PageHeader, Panel, StatTile } from "@/components/common/Panel";
import { ErrorState, EmptyState, LoadingBlock } from "@/components/common/States";
import { axisProps, ChartTooltip, gridProps, Legend } from "@/components/charts/ChartBits";
import { useHistory, useModelMetrics } from "@/hooks/queries";
import { pct, seasonLabel, shortDate } from "@/lib/format";
import { cn } from "@/lib/utils";

const FEATURE_LABELS: Record<string, string> = {
  elo_diff: "Elo difference", home_elo: "Home Elo", away_elo: "Away Elo",
  h_gf5: "Home goals for (5)", h_ga5: "Home goals against (5)", h_ppg5: "Home PPG (5)",
  a_gf5: "Away goals for (5)", a_ga5: "Away goals against (5)", a_ppg5: "Away PPG (5)",
  h_gf10: "Home goals for (10)", h_ga10: "Home goals against (10)", a_gf10: "Away goals for (10)", a_ga10: "Away goals against (10)",
  h_home_ppg: "Home side's home PPG", h_home_gf: "Home side's home goals", a_away_ppg: "Away side's away PPG", a_away_gf: "Away side's away goals",
  h_rest: "Home rest days", a_rest: "Away rest days", h2h_home_ppg: "Head-to-head PPG",
};

function History() {
  const { data, isLoading } = useHistory(30);
  return (
    <Panel title="Recent predictions" subtitle={data ? `${data.total} predictions made with this server` : undefined} bodyClassName="px-2 pb-3 pt-1">
      {isLoading ? <LoadingBlock rows={5} /> : !data?.items.length ? <EmptyState title="No predictions yet"><Link className="underline" to="/predict">Make one →</Link></EmptyState> : (
        <div className="max-h-[420px] overflow-auto scrollbar-thin">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="sticky top-0 bg-card text-xs text-muted-foreground">
              <tr><th className="px-2 py-1.5 text-left font-medium">Match</th><th className="py-1.5 text-right font-medium">1</th><th className="py-1.5 text-right font-medium">X</th><th className="py-1.5 text-right font-medium">2</th><th className="py-1.5 text-right font-medium">Score</th><th className="px-2 py-1.5 text-right font-medium">When</th></tr>
            </thead>
            <tbody>
              {data.items.map((h) => (
                <tr key={h.id} className="border-t">
                  <td className="px-2 py-1.5">
                    <Link className="hover:underline" to={`/predict?home=${encodeURIComponent(h.home_team)}&away=${encodeURIComponent(h.away_team)}`}>{h.home_team} vs {h.away_team}</Link>
                  </td>
                  {[h.home_win_prob, h.draw_prob, h.away_win_prob].map((v, i) => {
                    const best = Math.max(h.home_win_prob, h.draw_prob, h.away_win_prob) === v;
                    return <td key={i} className={cn("py-1.5 text-right tabular", best ? "font-semibold" : "text-muted-foreground")}>{pct(v * 100, 0)}</td>;
                  })}
                  <td className="py-1.5 text-right font-mono tabular">{h.predicted_score}</td>
                  <td className="px-2 py-1.5 text-right text-xs text-muted-foreground">{shortDate(h.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

export default function ModelLab() {
  const { data: m, isLoading, error, refetch } = useModelMetrics();
  if (isLoading) return <LoadingBlock rows={8} />;
  if (error || !m) return <ErrorState error={error} onRetry={refetch} />;
  if (!m.models) return <EmptyState title={`Model status: ${m.status}`}>Metrics appear once training finishes.</EmptyState>;
  const ens = m.models.find((r) => r.model.startsWith("Stacked"))!;
  const base = m.models.find((r) => r.model.startsWith("Baseline"))!;
  const calib = (m.calibration ?? []).map((c) => ({ ...c, predicted: c.predicted * 100, observed: c.observed * 100 }));
  const imp = (m.feature_importance ?? []).slice(0, 12).map((f) => ({ name: FEATURE_LABELS[f.feature] ?? f.feature, value: f.importance * 100 }));
  const best = (key: "accuracy" | "log_loss" | "rps" | "brier") => {
    const vals = m.models!.map((r) => r[key]);
    return key === "accuracy" ? Math.max(...vals) : Math.min(...vals);
  };
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Transparency" title="Model lab"
        description="How the prediction engine is built and how it performs on matches it has never seen (walk-forward backtest, no future data)." />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Out-of-sample accuracy" value={pct(ens.accuracy * 100)} sub={`vs ${pct(base.accuracy * 100)} class-frequency baseline`} />
        <StatTile label="Ranked probability score" value={ens.rps.toFixed(4)} sub={`Baseline ${base.rps.toFixed(4)} · lower is better`} />
        <StatTile label="Log loss" value={ens.log_loss.toFixed(4)} sub={`Baseline ${base.log_loss.toFixed(4)}`} />
        <StatTile label="Training data" value={`${m.matches} matches`} sub={`${m.seasons?.map(seasonLabel).join(", ")} · evaluated on ${m.evaluation_rows}`} />
      </div>

      <Panel title="Backtest leaderboard" subtitle="Same evaluation window for every model · best value in bold" bodyClassName="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="border-b bg-muted/40 text-xs text-muted-foreground">
              <tr><th className="px-4 py-2.5 text-left font-medium">Model</th><th className="px-3 py-2.5 text-right font-medium">Accuracy ↑</th><th className="px-3 py-2.5 text-right font-medium">RPS ↓</th><th className="px-3 py-2.5 text-right font-medium">Log loss ↓</th><th className="px-4 py-2.5 text-right font-medium">Brier ↓</th></tr>
            </thead>
            <tbody>
              {m.models.map((r) => (
                <tr key={r.model} className={cn("border-b last:border-0", r.model.startsWith("Stacked") && "bg-muted/30")}>
                  <td className="px-4 py-2.5 font-medium">{r.model}</td>
                  {(["accuracy", "rps", "log_loss", "brier"] as const).map((k) => (
                    <td key={k} className={cn("px-3 py-2.5 text-right tabular", r[k] === best(k) ? "font-bold" : "text-muted-foreground")}>
                      {k === "accuracy" ? pct(r[k] * 100) : r[k].toFixed(4)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Calibration" subtitle="When the model says X%, how often does it happen? Points near the diagonal = well calibrated.">
          <Legend className="mb-2" items={[{ label: "Observed frequency", color: "var(--series-home)" }, { label: "Perfect calibration", color: "var(--series-draw)" }]} />
          <div className="h-72">
            <ResponsiveContainer>
              <ComposedChart data={calib} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid {...gridProps} vertical />
                <XAxis type="number" dataKey="predicted" domain={[0, 100]} {...axisProps} tickFormatter={(v) => `${v}%`} />
                <YAxis type="number" domain={[0, 100]} {...axisProps} tickFormatter={(v) => `${v}%`} />
                <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 100, y: 100 }]} stroke="var(--series-draw)" strokeWidth={1} />
                <RTooltip content={<ChartTooltip formatter={(v) => pct(Number(v))} labelFormatter={(l) => `Predicted ≈ ${Number(l).toFixed(0)}%`} />} />
                <Line dataKey="observed" name="Observed" stroke="var(--series-home)" strokeWidth={2} dot={false} />
                <Scatter dataKey="observed" name="Observed" fill="var(--series-home)" stroke="var(--chart-surface)" strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Feature importance" subtitle="Average across the tree models (%)">
          <div className="h-[316px]">
            <ResponsiveContainer>
              <BarChart data={imp} layout="vertical" margin={{ top: 0, right: 36, left: 8, bottom: 0 }}>
                <CartesianGrid {...gridProps} horizontal={false} vertical />
                <XAxis type="number" {...axisProps} />
                <YAxis type="category" dataKey="name" width={170} {...axisProps} axisLine={false} interval={0} tick={{ ...axisProps.tick, fontSize: 10 }} />
                <RTooltip cursor={{ fill: "var(--chart-grid)", opacity: 0.4 }} content={<ChartTooltip formatter={(v) => `${Number(v).toFixed(1)}%`} />} />
                <Bar dataKey="value" name="Importance" fill="var(--seq-500)" radius={[0, 4, 4, 0]} maxBarSize={16}
                  label={{ position: "right", fill: "var(--chart-axis)", fontSize: 10, formatter: (v: number) => v.toFixed(1) }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="Accuracy by confidence" subtitle="Higher-confidence picks should hit more often">
          <ul className="space-y-3">
            {m.confidence_buckets?.map((b) => (
              <li key={b.bucket} className="text-sm">
                <div className="mb-1 flex justify-between"><span className="text-muted-foreground">Confidence {b.bucket}</span><span className="tabular"><b>{b.accuracy !== null ? pct(b.accuracy * 100, 0) : "—"}</b> <span className="text-xs text-muted-foreground">of {b.count}</span></span></div>
                <div className="h-2 rounded-full bg-muted"><div className="h-full rounded-full" style={{ width: `${(b.accuracy ?? 0) * 100}%`, background: "var(--seq-500)" }} /></div>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Ensemble configuration">
          <dl className="space-y-2 text-sm">
            {[
              ["Meta-learner", m.meta_learner?.replace("_", " ")],
              ["Calibration temperature", m.temperature?.toFixed(3)],
              ["Dixon-Coles half-life", `${m.half_life_days} days`],
              ["Home advantage (goals ×)", m.poisson?.home_advantage.toFixed(3)],
              ["Low-score correction ρ", m.poisson?.rho.toFixed(3)],
              ["Trained", shortDate(m.trained_at)],
              ["Training time", `${m.training_seconds}s`],
            ].map(([k, v]) => (
              <div key={k as string} className="flex justify-between gap-3"><dt className="text-muted-foreground">{k}</dt><dd className="font-medium tabular first-letter:uppercase">{v}</dd></div>
            ))}
          </dl>
          {m.blend_weights && (
            <div className="mt-4">
              <div className="mb-2 text-xs font-medium text-muted-foreground">Blend weights</div>
              {Object.entries(m.blend_weights).map(([k, v]) => (
                <div key={k} className="mb-1.5 grid grid-cols-[7rem_1fr_3rem] items-center gap-2 text-xs">
                  <span className="capitalize text-muted-foreground">{k.replace("_", " ")}</span>
                  <div className="h-1.5 rounded-full bg-muted"><div className="h-full rounded-full" style={{ width: `${v * 100}%`, background: "var(--seq-500)" }} /></div>
                  <span className="text-right tabular">{pct(v * 100, 0)}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
        <Panel title="Outcome base rates" subtitle="Share of results in the training data">
          {m.outcome_distribution && (
            <div className="space-y-3">
              {[["Home wins", m.outcome_distribution.home, "var(--series-home)"], ["Draws", m.outcome_distribution.draw, "var(--series-draw)"], ["Away wins", m.outcome_distribution.away, "var(--series-away)"]].map(([l, v, c]) => (
                <div key={l as string} className="text-sm">
                  <div className="mb-1 flex justify-between"><span className="text-muted-foreground">{l as string}</span><b className="tabular">{pct((v as number) * 100)}</b></div>
                  <div className="h-2 rounded-full bg-muted"><div className="h-full rounded-full" style={{ width: `${(v as number) * 100}%`, background: c as string }} /></div>
                </div>
              ))}
            </div>
          )}
          {m.half_life_sweep && (
            <div className="mt-5">
              <div className="mb-2 text-xs font-medium text-muted-foreground">Dixon-Coles half-life sweep (RPS)</div>
              <div className="h-32">
                <ResponsiveContainer>
                  <LineChart data={m.half_life_sweep} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid {...gridProps} />
                    <XAxis dataKey="half_life" {...axisProps} tickFormatter={(v) => `${v}d`} />
                    <YAxis {...axisProps} domain={["dataMin - 0.001", "dataMax + 0.001"]} tickFormatter={(v) => Number(v).toFixed(3)} />
                    <RTooltip content={<ChartTooltip formatter={(v) => Number(v).toFixed(4)} labelFormatter={(l) => `Half-life ${l} days`} />} />
                    <Line dataKey="rps" name="RPS" stroke="var(--series-home)" strokeWidth={2} dot={{ r: 4, fill: "var(--series-home)", stroke: "var(--chart-surface)", strokeWidth: 2 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </Panel>
      </div>

      <History />
    </div>
  );
}

import { Link, useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { Activity, ArrowRight, Database, HeartPulse, Sparkles, Target, Users } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, StatTile } from "@/components/common/Panel";
import { PlayerAvatar, TeamCrest } from "@/components/common/Crest";
import { FormPills } from "@/components/common/Form";
import { TeamPicker } from "@/components/common/Pickers";
import { LoadingBlock } from "@/components/common/States";
import { StatusChip } from "@/components/common/StatusChip";
import { FixtureCard } from "@/components/matches/FixtureCard";
import { axisProps, ChartTooltip, gridProps } from "@/components/charts/ChartBits";
import { useHealth, useInjuries, useLeaders, useLive, useModelMetrics, usePowerRankings, useSimulatedRound, useStandings, useUpcoming } from "@/hooks/queries";
import { num, pct, seasonLabel, shortDate } from "@/lib/format";
import { cn } from "@/lib/utils";

const zoneColor: Record<string, string> = {
  champions_league: "var(--series-home)",
  europa_league: "var(--series-3)",
  conference_league: "var(--series-4)",
  relegation: "var(--critical)",
};

function QuickPredict() {
  const [home, setHome] = useState<string | null>("Real Madrid");
  const [away, setAway] = useState<string | null>("Barcelona");
  const navigate = useNavigate();
  return (
    <section className="relative overflow-hidden rounded-2xl border bg-card p-5 shadow-sm md:p-7">
      <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full opacity-25 blur-3xl" style={{ background: "hsl(var(--primary))" }} />
      <div className="relative grid gap-6 lg:grid-cols-[1.1fr_1fr] lg:items-center">
        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
            <Sparkles className="h-3 w-3 text-primary" /> Calibrated ensemble model
          </div>
          <h2 className="text-balance text-2xl font-bold tracking-tight md:text-3xl">Who wins the next LaLiga match?</h2>
          <p className="mt-2 max-w-lg text-sm text-muted-foreground">
            Dixon-Coles Poisson + XGBoost, LightGBM and Random Forest, blended and calibrated by walk-forward validation, with injury-adjusted expected goals.
          </p>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <TeamPicker label="Home" value={home} onChange={setHome} exclude={away} />
          <TeamPicker label="Away" value={away} onChange={setAway} exclude={home} />
          <Button size="lg" className="sm:col-span-2" disabled={!home || !away}
            onClick={() => navigate(`/predict?home=${encodeURIComponent(home!)}&away=${encodeURIComponent(away!)}`)}>
            <Target className="mr-2 h-4 w-4" /> Analyse match
          </Button>
        </div>
      </div>
    </section>
  );
}

function Kpis() {
  const { data: m } = useModelMetrics();
  const { data: h } = useHealth();
  const ens = m?.models?.find((r) => r.model.startsWith("Stacked"));
  const base = m?.models?.find((r) => r.model.startsWith("Baseline"));
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatTile label="Backtest accuracy" icon={<Target className="h-4 w-4" />} value={ens ? pct(ens.accuracy * 100) : "—"}
        sub={base ? `Baseline ${pct(base.accuracy * 100)} · ${ens?.n} matches` : "Walk-forward out-of-sample"} />
      <StatTile label="Ranked probability score" icon={<Activity className="h-4 w-4" />} value={ens ? ens.rps.toFixed(4) : "—"}
        sub={base && ens ? `${(((base.rps - ens.rps) / base.rps) * 100).toFixed(1)}% better than baseline · lower is better` : "Lower is better"} />
      <StatTile label="Matches analysed" icon={<Database className="h-4 w-4" />} value={h ? num(h.data.matches) : "—"}
        sub={h ? `Seasons ${m?.seasons?.map((s) => seasonLabel(s)).join(", ") ?? ""}` : ""} />
      <StatTile label="Players tracked" icon={<Users className="h-4 w-4" />} value={h ? num(h.data.players) : "—"}
        sub={h ? `Season ${seasonLabel(h.data.player_season)} · data to ${shortDate(h.data.data_as_of)}` : ""} />
    </div>
  );
}

function MatchesStrip() {
  const live = useLive();
  const upcoming = useUpcoming();
  const sim = useSimulatedRound();
  const liveRows = live.data?.matches ?? [];
  const upRows = upcoming.data?.matches ?? [];
  if (liveRows.length) {
    return (
      <Panel title="Live now" action={<Button asChild variant="ghost" size="sm"><Link to="/matches">All matches <ArrowRight className="ml-1 h-3.5 w-3.5" /></Link></Button>}>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {liveRows.map((f) => (
            <FixtureCard key={f.id} home={f.home_team} away={f.away_team} homeLogo={f.home_logo} awayLogo={f.away_logo}
              top={f.round} live elapsed={f.elapsed} score={{ home: f.home_score, away: f.away_score }} />
          ))}
        </div>
      </Panel>
    );
  }
  const rows = upRows.length
    ? upRows.map((f) => ({ key: String(f.id), home: f.home_team, away: f.away_team, hl: f.home_logo, al: f.away_logo, top: f.round, prediction: f.prediction }))
    : (sim.data?.matches ?? []).slice(0, 6).map((m) => ({ key: m.home_team + m.away_team, home: m.home_team, away: m.away_team, hl: m.home_logo, al: m.away_logo, top: "Simulated fixture", prediction: m.prediction }));
  return (
    <Panel title={upRows.length ? "Upcoming fixtures" : "Model picks"}
      subtitle={upRows.length ? "Next 48 hours, with model predictions" : "No LaLiga fixtures in the API window — model picks for a simulated matchday"}
      action={<Button asChild variant="ghost" size="sm"><Link to="/matches">Matches <ArrowRight className="ml-1 h-3.5 w-3.5" /></Link></Button>}>
      {sim.isLoading && upcoming.isLoading ? <LoadingBlock rows={3} /> : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map((r) => (
            <FixtureCard key={r.key} home={r.home} away={r.away} homeLogo={r.hl} awayLogo={r.al} top={r.top} prediction={r.prediction} />
          ))}
        </div>
      )}
    </Panel>
  );
}

function MiniTable() {
  const { data, isLoading } = useStandings();
  return (
    <Panel title="League table" subtitle={data ? `Season ${seasonLabel(data.season)}` : undefined}
      action={<Button asChild variant="ghost" size="sm"><Link to="/standings">Full table <ArrowRight className="ml-1 h-3.5 w-3.5" /></Link></Button>}
      bodyClassName="px-2 pb-3 pt-2">
      {isLoading ? <LoadingBlock rows={6} className="px-3" /> : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] text-muted-foreground">
              <th className="w-8 py-1.5 text-left font-medium" />
              <th className="py-1.5 text-left font-medium">Team</th>
              <th className="py-1.5 text-right font-medium">GD</th>
              <th className="py-1.5 pr-3 text-right font-medium">Pts</th>
            </tr>
          </thead>
          <tbody>
            {data?.table.slice(0, 8).map((r) => (
              <tr key={r.team} className="border-t">
                <td className="py-1.5">
                  <span className="flex items-center gap-1.5 pl-1 text-xs text-muted-foreground tabular">
                    <span className="h-4 w-1 rounded-full" style={{ background: r.zone ? zoneColor[r.zone] : "transparent" }} aria-hidden />
                    {r.rank}
                  </span>
                </td>
                <td className="py-1.5">
                  <Link to={`/teams/${encodeURIComponent(r.team)}`} className="flex items-center gap-2 hover:underline">
                    <TeamCrest team={r.team} logo={r.logo} size="xs" /> <span className="truncate">{r.team}</span>
                  </Link>
                </td>
                <td className="py-1.5 text-right text-muted-foreground tabular">{r.goal_diff > 0 ? `+${r.goal_diff}` : r.goal_diff}</td>
                <td className="py-1.5 pr-3 text-right font-semibold tabular">{r.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}

function PowerChart() {
  const { data } = usePowerRankings();
  const rows = (data?.items ?? []).slice(0, 10).map((r) => ({ team: r.team, elo: Math.round(r.elo) }));
  const min = rows.length ? Math.floor((Math.min(...rows.map((r) => r.elo)) - 40) / 50) * 50 : 1300;
  return (
    <Panel title="Power rankings" subtitle="Top 10 by Elo rating"
      action={<Button asChild variant="ghost" size="sm"><Link to="/standings?tab=power">Details <ArrowRight className="ml-1 h-3.5 w-3.5" /></Link></Button>}>
      <div className="h-72">
        <ResponsiveContainer>
          <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 40, left: 8, bottom: 0 }}>
            <CartesianGrid {...gridProps} horizontal={false} vertical />
            <XAxis type="number" domain={[min, "dataMax"]} {...axisProps} />
            <YAxis type="category" dataKey="team" width={110} {...axisProps} axisLine={false} interval={0} />
            <RTooltip cursor={{ fill: "var(--chart-grid)", opacity: 0.4 }} content={<ChartTooltip />} />
            <Bar dataKey="elo" name="Elo" fill="var(--seq-500)" radius={[0, 4, 4, 0]} maxBarSize={18}
              label={{ position: "right", fill: "var(--chart-axis)", fontSize: 11 }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

function LeadersPanel() {
  const { data, isLoading } = useLeaders(5);
  const [tab, setTab] = useState<"goals" | "assists" | "rating">("goals");
  const rows = data?.[tab] ?? [];
  return (
    <Panel title="Top performers" subtitle={data ? `Season ${seasonLabel(data.season)}` : undefined}
      action={
        <div className="flex rounded-lg border p-0.5 text-xs">
          {(["goals", "assists", "rating"] as const).map((k) => (
            <button key={k} onClick={() => setTab(k)} className={cn("rounded-md px-2 py-1 capitalize", tab === k ? "bg-muted font-medium" : "text-muted-foreground")}>{k}</button>
          ))}
        </div>
      }>
      {isLoading ? <LoadingBlock rows={5} /> : (
        <ol className="space-y-2.5">
          {rows.map((p, i) => (
            <li key={p.id}>
              <Link to={`/players/${p.id}`} className="flex items-center gap-3 rounded-lg p-1 hover:bg-muted/60">
                <span className="w-4 text-xs text-muted-foreground tabular">{i + 1}</span>
                <PlayerAvatar name={p.name} photo={p.photo} size="sm" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{p.name}</span>
                  <span className="block truncate text-xs text-muted-foreground">{p.team}</span>
                </span>
                <span className="text-lg font-semibold tabular">{tab === "rating" ? p.value?.toFixed(2) : p.value}</span>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}

function InjurySummary() {
  const { data, isLoading } = useInjuries();
  return (
    <Panel title="Availability" subtitle={data ? `As of ${shortDate(data.as_of)}` : undefined}
      action={<Button asChild variant="ghost" size="sm"><Link to="/injuries">Tracker <ArrowRight className="ml-1 h-3.5 w-3.5" /></Link></Button>}>
      {isLoading || !data ? <LoadingBlock rows={4} /> : (
        <>
          <div className="mb-4 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-muted/50 py-2"><div className="text-xl font-semibold tabular">{data.summary.out}</div><div className="text-[11px] text-muted-foreground">Injured</div></div>
            <div className="rounded-lg bg-muted/50 py-2"><div className="text-xl font-semibold tabular">{data.summary.suspended}</div><div className="text-[11px] text-muted-foreground">Suspended</div></div>
            <div className="rounded-lg bg-muted/50 py-2"><div className="text-xl font-semibold tabular">{data.summary.doubtful}</div><div className="text-[11px] text-muted-foreground">Doubtful</div></div>
          </div>
          <ul className="space-y-2">
            {[...data.current].sort((a, b) => (b.goals ?? 0) + (b.assists ?? 0) - ((a.goals ?? 0) + (a.assists ?? 0))).slice(0, 5).map((e) => (
              <li key={e.player_id} className="flex items-center gap-2.5">
                <PlayerAvatar name={e.player} photo={e.photo} size="sm" />
                <span className="min-w-0 flex-1">
                  <Link to={`/players/${e.player_id}`} className="block truncate text-sm font-medium hover:underline">{e.player}</Link>
                  <span className="block truncate text-xs text-muted-foreground">{e.team} · {e.reason}</span>
                </span>
                <StatusChip status={e.status} />
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}

function FormGuide() {
  const { data } = useStandings();
  const rows = [...(data?.table ?? [])].map((r) => ({ ...r, formPts: r.form.split("").reduce((s, c) => s + (c === "W" ? 3 : c === "D" ? 1 : 0), 0) }))
    .sort((a, b) => b.formPts - a.formPts).slice(0, 6);
  return (
    <Panel title="In-form teams" subtitle="Points from the last five matches">
      <ul className="space-y-2.5">
        {rows.map((r) => (
          <li key={r.team} className="flex items-center gap-2.5">
            <TeamCrest team={r.team} logo={r.logo} size="sm" />
            <Link to={`/teams/${encodeURIComponent(r.team)}`} className="min-w-0 flex-1 truncate text-sm font-medium hover:underline">{r.team}</Link>
            <FormPills form={r.form} />
            <span className="w-6 text-right text-sm font-semibold tabular">{r.formPts}</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export default function Dashboard() {
  const { data: h } = useHealth();
  return (
    <div className="space-y-6">
      <PageHeader eyebrow={h ? `LaLiga · season ${seasonLabel(h.data.latest_season)}` : "LaLiga"} title="Analytics dashboard"
        description="Predictions, team strength, player performance and availability in one place." />
      <QuickPredict />
      <Kpis />
      <MatchesStrip />
      <div className="grid gap-6 lg:grid-cols-3">
        <MiniTable />
        <LeadersPanel />
        <InjurySummary />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2"><PowerChart /></div>
        <FormGuide />
      </div>
      <p className="flex items-center justify-center gap-1.5 text-center text-[11px] text-muted-foreground">
        <HeartPulse className="h-3 w-3" /> Historical data: API-Football (free plan covers seasons 2022–2024). Live scores use the same API with caching.
      </p>
    </div>
  );
}

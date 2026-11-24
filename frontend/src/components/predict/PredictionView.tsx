import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { ArrowDownRight, ArrowUpRight, CircleMinus, Info } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import type { Prediction, TeamCard } from "@/api/types";
import { Panel, StatTile } from "@/components/common/Panel";
import { PlayerAvatar, TeamCrest } from "@/components/common/Crest";
import { FormPills } from "@/components/common/Form";
import { Meter, ProbabilityBar } from "@/components/common/Probability";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState } from "@/components/common/States";
import { axisProps, ChartTooltip, gridProps, Legend } from "@/components/charts/ChartBits";
import { fairOdds, pct, shortDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ScoreHeatmap } from "./ScoreHeatmap";

const levelStyles = {
  high: "border-good/40 bg-good/10 text-good-text",
  medium: "border-warning/50 bg-warning/10 text-foreground",
  low: "border-border bg-muted text-muted-foreground",
};

function Hero({ p }: { p: Prediction }) {
  const [hs, as] = p.predicted_score.split("-");
  return (
    <section className="overflow-hidden rounded-2xl border bg-card shadow-sm">
      <div className="relative px-5 pb-6 pt-6 md:px-10">
        <div className="pointer-events-none absolute inset-0 opacity-60"
          style={{ background: "radial-gradient(600px 200px at 15% 0%, color-mix(in srgb, var(--series-home) 14%, transparent), transparent), radial-gradient(600px 200px at 85% 0%, color-mix(in srgb, var(--series-away) 14%, transparent), transparent)" }} />
        <div className="relative grid grid-cols-[1fr_auto_1fr] items-center gap-3 md:gap-8">
          <Link to={`/teams/${encodeURIComponent(p.home_team)}`} className="flex flex-col items-center gap-2 text-center md:flex-row md:justify-end md:text-right">
            <span className="order-2 md:order-1">
              <span className="block text-base font-bold leading-tight md:text-xl">{p.home_team}</span>
              <span className="text-xs text-muted-foreground">Home · Elo {Math.round(p.teams.home.elo)}</span>
            </span>
            <TeamCrest team={p.home_team} logo={p.home_logo} size="xl" className="order-1 md:order-2" />
          </Link>
          <div className="flex flex-col items-center">
            <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Most likely score</div>
            <div className="mt-1 flex items-center gap-3 font-mono text-4xl font-semibold tabular md:text-6xl">
              <span>{hs}</span><span className="text-muted-foreground">:</span><span>{as}</span>
            </div>
            <div className="mt-1 text-xs text-muted-foreground tabular">xG {p.expected_goals.home.toFixed(2)} – {p.expected_goals.away.toFixed(2)}</div>
          </div>
          <Link to={`/teams/${encodeURIComponent(p.away_team)}`} className="flex flex-col items-center gap-2 text-center md:flex-row md:text-left">
            <TeamCrest team={p.away_team} logo={p.away_logo} size="xl" />
            <span>
              <span className="block text-base font-bold leading-tight md:text-xl">{p.away_team}</span>
              <span className="text-xs text-muted-foreground">Away · Elo {Math.round(p.teams.away.elo)}</span>
            </span>
          </Link>
        </div>

        <div className="relative mx-auto mt-6 max-w-2xl">
          <ProbabilityBar home={p.probabilities.home_win} draw={p.probabilities.draw} away={p.probabilities.away_win}
            homeLabel={p.home_team} awayLabel={p.away_team} height="h-3.5" />
        </div>

        <div className="relative mt-5 flex flex-wrap items-center justify-center gap-2 text-xs">
          <span className={cn("rounded-full border px-2.5 py-1 font-medium", levelStyles[p.confidence_level])}>
            Pick: {p.predicted_outcome_label} · {pct(p.confidence)}
          </span>
          <span className="rounded-full border px-2.5 py-1 text-muted-foreground">
            {p.model_agreement.agreeing_models}/{p.model_agreement.total_models} models agree
          </span>
          {p.availability.applied && (p.availability.home.players.length > 0 || p.availability.away.players.length > 0) && (
            <span className="rounded-full border px-2.5 py-1 text-muted-foreground">Adjusted for {p.availability.home.players.length + p.availability.away.players.length} absences</span>
          )}
        </div>
      </div>
    </section>
  );
}

function Factors({ p }: { p: Prediction }) {
  return (
    <Panel title="Why this prediction" subtitle="Main drivers, signed towards the team they favour">
      <ul className="space-y-3">
        {p.factors.map((f) => {
          const Icon = f.direction === "home" ? ArrowUpRight : f.direction === "away" ? ArrowDownRight : CircleMinus;
          const color = f.direction === "home" ? "var(--series-home)" : f.direction === "away" ? "var(--series-away)" : "var(--series-draw)";
          return (
            <li key={f.label} className="flex items-start gap-3">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full" style={{ background: `color-mix(in srgb, ${color} 18%, transparent)` }}>
                <Icon className="h-3.5 w-3.5" style={{ color }} aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline justify-between gap-x-2">
                  <span className="text-sm font-medium">{f.label}</span>
                  <span className="text-xs text-muted-foreground">
                    {f.direction === "neutral" ? "Neutral" : `Favours ${f.direction === "home" ? p.home_team : p.away_team}`}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{f.detail}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

function MarketRow({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="min-w-0 flex-1">
        <div className="text-sm">{label}</div>
        {hint && <div className="text-[11px] text-muted-foreground">{hint}</div>}
      </div>
      <div className="hidden w-32 sm:block">
        <div className="h-1.5 rounded-full" style={{ background: "color-mix(in srgb, var(--series-home) 18%, transparent)" }}>
          <div className="h-full rounded-full" style={{ width: `${value}%`, background: "var(--series-home)" }} />
        </div>
      </div>
      <div className="w-14 text-right text-sm font-semibold tabular">{pct(value)}</div>
      <div className="w-12 text-right text-xs text-muted-foreground tabular" title="Fair decimal odds">{fairOdds(value)}</div>
    </div>
  );
}

function Markets({ p }: { p: Prediction }) {
  const m = p.markets;
  const totals = m.total_goals_dist.map((v, i) => ({ goals: i === 7 ? "7+" : String(i), p: v }));
  const teamGoals = m.home_goals_dist.map((v, i) => ({ goals: i === 5 ? "5+" : String(i), home: v, away: m.away_goals_dist[i] }));
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Goal lines" subtitle="Probability · fair decimal odds">
        <div className="divide-y">
          <MarketRow label="Over 1.5 goals" value={m.over_1_5} hint={`Under 1.5: ${pct(m.under_1_5)}`} />
          <MarketRow label="Over 2.5 goals" value={m.over_2_5} hint={`Under 2.5: ${pct(m.under_2_5)}`} />
          <MarketRow label="Over 3.5 goals" value={m.over_3_5} hint={`Under 3.5: ${pct(m.under_3_5)}`} />
          <MarketRow label="Over 4.5 goals" value={m.over_4_5} />
        </div>
      </Panel>
      <Panel title="Both teams & clean sheets">
        <div className="divide-y">
          <MarketRow label="Both teams to score — Yes" value={m.btts_yes} hint={`No: ${pct(m.btts_no)}`} />
          <MarketRow label={`${p.home_team} to score`} value={m.home_to_score} />
          <MarketRow label={`${p.away_team} to score`} value={m.away_to_score} />
          <MarketRow label={`${p.home_team} clean sheet`} value={m.home_clean_sheet} />
          <MarketRow label={`${p.away_team} clean sheet`} value={m.away_clean_sheet} />
        </div>
      </Panel>
      <Panel title="Double chance & draw no bet">
        <div className="divide-y">
          <MarketRow label={`1X · ${p.home_team} or draw`} value={m.double_chance_1x} />
          <MarketRow label={`X2 · ${p.away_team} or draw`} value={m.double_chance_x2} />
          <MarketRow label="12 · No draw" value={m.double_chance_12} />
          <MarketRow label={`Draw no bet · ${p.home_team}`} value={m.draw_no_bet_home} hint={`${p.away_team}: ${pct(100 - m.draw_no_bet_home)}`} />
        </div>
      </Panel>
      <Panel title="Total goals in the match" subtitle="Probability of each total (%)">
        <div className="h-56">
          <ResponsiveContainer>
            <BarChart data={totals} margin={{ top: 16, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="goals" {...axisProps} />
              <YAxis {...axisProps} tickFormatter={(v) => `${v}`} />
              <RTooltip cursor={{ fill: "var(--chart-grid)", opacity: 0.4 }} content={<ChartTooltip formatter={(v) => pct(Number(v))} labelFormatter={(l) => `${l} goals`} />} />
              <Bar dataKey="p" name="Probability" fill="var(--seq-500)" radius={[4, 4, 0, 0]} maxBarSize={24}
                label={{ position: "top", fill: "var(--chart-axis)", fontSize: 10, formatter: (v: number) => (v >= 10 ? v.toFixed(0) : "") }} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <Panel title="Goals per team" subtitle="Probability each team scores exactly N goals (%)" className="lg:col-span-2">
        <Legend className="mb-2" items={[{ label: p.home_team, color: "var(--series-home)" }, { label: p.away_team, color: "var(--series-away)" }]} />
        <div className="h-56">
          <ResponsiveContainer>
            <BarChart data={teamGoals} margin={{ top: 8, right: 8, left: -16, bottom: 0 }} barGap={2}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="goals" {...axisProps} />
              <YAxis {...axisProps} />
              <RTooltip cursor={{ fill: "var(--chart-grid)", opacity: 0.4 }} content={<ChartTooltip formatter={(v) => pct(Number(v))} labelFormatter={(l) => `${l} goals`} />} />
              <Bar dataKey="home" name={p.home_team} fill="var(--series-home)" radius={[4, 4, 0, 0]} maxBarSize={24} />
              <Bar dataKey="away" name={p.away_team} fill="var(--series-away)" radius={[4, 4, 0, 0]} maxBarSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  );
}

function Scorelines({ p }: { p: Prediction }) {
  const margin = p.markets.winning_margin;
  const marginRows = [
    { k: "home_3plus", l: `${p.home_team} by 3+` }, { k: "home_by_2", l: `${p.home_team} by 2` }, { k: "home_by_1", l: `${p.home_team} by 1` },
    { k: "draw", l: "Draw" },
    { k: "away_by_1", l: `${p.away_team} by 1` }, { k: "away_by_2", l: `${p.away_team} by 2` }, { k: "away_3plus", l: `${p.away_team} by 3+` },
  ];
  return (
    <div className="grid gap-4 lg:grid-cols-5">
      <Panel title="Scoreline probabilities" subtitle="Dixon-Coles score matrix, re-weighted to the ensemble's 1X2" className="lg:col-span-3">
        <ScoreHeatmap matrix={p.score_matrix} home={p.home_team} away={p.away_team} highlight={p.predicted_score} />
      </Panel>
      <div className="space-y-4 lg:col-span-2">
        <Panel title="Top 10 correct scores">
          <ol className="space-y-1.5">
            {p.scorelines.map((s, i) => (
              <li key={s.score} className="flex items-center gap-3 text-sm">
                <span className="w-5 text-right text-xs text-muted-foreground tabular">{i + 1}</span>
                <span className="w-12 font-mono font-semibold tabular">{s.score}</span>
                <div className="h-1.5 flex-1 rounded-full bg-muted">
                  <div className="h-full rounded-full" style={{
                    width: `${(s.prob / p.scorelines[0].prob) * 100}%`,
                    background: s.home > s.away ? "var(--series-home)" : s.home < s.away ? "var(--series-away)" : "var(--series-draw)",
                  }} />
                </div>
                <span className="w-12 text-right font-medium tabular">{pct(s.prob)}</span>
              </li>
            ))}
          </ol>
        </Panel>
        <Panel title="Winning margin">
          <div className="space-y-2">
            {marginRows.map((r) => (
              <div key={r.k} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{r.l}</span>
                <span className="font-semibold tabular">{pct(margin[r.k])}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Models({ p }: { p: Prediction }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Panel title="Model breakdown" subtitle="Each base model's 1X2 probabilities vs. the calibrated ensemble" className="lg:col-span-2">
        <div className="space-y-5">
          {p.models.map((m) => (
            <div key={m.key}>
              <div className="mb-1.5 text-sm font-medium">{m.name}</div>
              <ProbabilityBar home={m.home_win} draw={m.draw} away={m.away_win} homeLabel={p.home_team} awayLabel={p.away_team} height="h-2.5" />
            </div>
          ))}
          <div className="rounded-lg border bg-muted/40 p-3">
            <div className="mb-1.5 text-sm font-semibold">Ensemble (final)</div>
            <ProbabilityBar home={p.probabilities.home_win} draw={p.probabilities.draw} away={p.probabilities.away_win} homeLabel={p.home_team} awayLabel={p.away_team} height="h-2.5" />
          </div>
        </div>
      </Panel>
      <div className="space-y-4">
        <StatTile label="Model agreement" value={<span className="capitalize">{p.model_agreement.level}</span>}
          sub={`${p.model_agreement.agreeing_models} of ${p.model_agreement.total_models} base models pick the same outcome · spread ±${p.model_agreement.spread.toFixed(1)} pts`} />
        <StatTile label="Confidence" value={pct(p.confidence)} sub={<span className="capitalize">{p.confidence_level} confidence pick</span>} />
        <Panel title="How it works">
          <p className="text-xs leading-relaxed text-muted-foreground">
            Dixon-Coles Poisson estimates attack/defence strengths with time decay. XGBoost, LightGBM and Random Forest learn from
            Elo, rolling form, venue records, rest and head-to-head. A meta-learner, chosen by walk-forward validation, blends
            them and a temperature step calibrates the result. <Link className="underline underline-offset-2" to="/model">See backtests →</Link>
          </p>
        </Panel>
      </div>
    </div>
  );
}

function TeamFormCard({ t, side }: { t: TeamCard; side: "home" | "away" }) {
  const s = t.season;
  return (
    <Panel title={<span className="flex items-center gap-2"><TeamCrest team={t.team} logo={t.logo} size="xs" /> {t.team}</span>}
      subtitle={side === "home" ? "Home side" : "Away side"} action={<FormPills form={t.form_string} />}>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div><div className="text-lg font-semibold tabular">{s.ppg?.toFixed(2)}</div><div className="text-[11px] text-muted-foreground">Points / game</div></div>
        <div><div className="text-lg font-semibold tabular">{s.avg_scored?.toFixed(2)}</div><div className="text-[11px] text-muted-foreground">Scored / game</div></div>
        <div><div className="text-lg font-semibold tabular">{s.avg_conceded?.toFixed(2)}</div><div className="text-[11px] text-muted-foreground">Conceded / game</div></div>
      </div>
      <ul className="mt-4 divide-y text-sm">
        {t.form.map((f) => (
          <li key={f.date + f.opponent} className="flex items-center gap-2 py-1.5">
            <FormPills form={f.result} />
            <span className="min-w-0 flex-1 truncate">{f.venue === "home" ? "vs" : "@"} {f.opponent}</span>
            <span className="font-mono tabular">{f.score}</span>
            <span className="w-16 text-right text-xs text-muted-foreground">{shortDate(f.date).replace(/, \d{4}/, "")}</span>
          </li>
        ))}
      </ul>
      {t.key_players.length > 0 && (
        <div className="mt-4">
          <div className="mb-2 text-xs font-medium text-muted-foreground">Key contributors</div>
          <div className="space-y-2">
            {t.key_players.map((kp) => (
              <Link key={kp.id} to={`/players/${kp.id}`} className="flex items-center gap-2 rounded-lg p-1 hover:bg-muted/60">
                <PlayerAvatar name={kp.name} photo={kp.photo} size="sm" />
                <span className="min-w-0 flex-1 truncate text-sm">{kp.name}</span>
                <span className="text-xs text-muted-foreground tabular">{kp.goals}G {kp.assists}A{kp.rating ? ` · ${kp.rating.toFixed(2)}` : ""}</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}

function FormH2H({ p }: { p: Prediction }) {
  const h = p.h2h;
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <TeamFormCard t={p.teams.home} side="home" />
      <Panel title="Head-to-head" subtitle={`${h.played} meetings in the data set`}>
        {h.played === 0 ? <EmptyState title="No previous meetings" /> : (
          <>
            <ProbabilityBar home={h.team_a_wins} draw={h.draws} away={h.team_b_wins} homeLabel={`${p.home_team} wins`} awayLabel={`${p.away_team} wins`} showLegend={false} />
            <div className="mt-3 grid grid-cols-3 text-center">
              <div><div className="text-xl font-semibold tabular">{h.team_a_wins}</div><div className="text-[11px] text-muted-foreground">{p.home_team}</div></div>
              <div><div className="text-xl font-semibold tabular">{h.draws}</div><div className="text-[11px] text-muted-foreground">Draws</div></div>
              <div><div className="text-xl font-semibold tabular">{h.team_b_wins}</div><div className="text-[11px] text-muted-foreground">{p.away_team}</div></div>
            </div>
            <div className="mt-3 flex justify-between text-xs text-muted-foreground">
              <span>Avg goals <b className="text-foreground tabular">{h.avg_goals}</b></span>
              <span>BTTS <b className="text-foreground tabular">{pct(h.btts_rate * 100, 0)}</b></span>
            </div>
            <ul className="mt-4 divide-y text-sm">
              {h.meetings.map((m) => (
                <li key={m.date} className="flex items-center gap-2 py-2">
                  <span className="w-20 text-xs text-muted-foreground">{shortDate(m.date)}</span>
                  <span className={cn("min-w-0 flex-1 truncate text-right", m.winner === m.home_team && "font-semibold")}>{m.home_team}</span>
                  <span className="rounded bg-muted px-1.5 font-mono text-xs tabular">{m.home_score}-{m.away_score}</span>
                  <span className={cn("min-w-0 flex-1 truncate", m.winner === m.away_team && "font-semibold")}>{m.away_team}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </Panel>
      <TeamFormCard t={p.teams.away} side="away" />
    </div>
  );
}

function Availability({ p }: { p: Prediction }) {
  const side = (team: string, imp: Prediction["availability"]["home"], base: number, adj: number) => (
    <Panel title={team} subtitle={imp.players.length ? `${imp.players.length} unavailable` : "Full squad available"}>
      <div className="mb-4 grid grid-cols-2 gap-3">
        <StatTile label="Expected goals" value={adj.toFixed(2)} sub={`Full strength: ${base.toFixed(2)}`} />
        <StatTile label="Attack strength" value={pct(imp.attack_multiplier * 100, 0)} sub="of full-strength output" />
      </div>
      {imp.players.length === 0 ? <EmptyState title="No reported absences" /> : (
        <ul className="divide-y text-sm">
          {imp.players.map((pl) => (
            <li key={pl.player_id} className="flex items-center gap-2 py-2">
              <Link to={`/players/${pl.player_id}`} className="min-w-0 flex-1 truncate hover:underline">{pl.player}</Link>
              <span className="hidden text-xs text-muted-foreground sm:inline">{pl.position}</span>
              <span className="text-xs text-muted-foreground tabular">{pl.goals}G {pl.assists}A</span>
              <StatusChip status={pl.status as never} />
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
  const w = p.probabilities_without_availability;
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2 rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>
          Absences reduce a team's expected goals by each player's share of goal contributions and minutes (capped at 15%). Missing
          goalkeepers and defenders raise the opponent's expected goals. Without adjustments the odds would be {p.home_team} {pct(w.home_win)} · Draw {pct(w.draw)} · {p.away_team} {pct(w.away_win)}.
        </span>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {side(p.home_team, p.availability.home, p.expected_goals.home_base, p.expected_goals.home)}
        {side(p.away_team, p.availability.away, p.expected_goals.away_base, p.expected_goals.away)}
      </div>
    </div>
  );
}

export function PredictionView({ p }: { p: Prediction }) {
  return (
    <div className="space-y-6 animate-in fade-in-0 slide-in-from-bottom-2 duration-500">
      <Hero p={p} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Meter label="Over 2.5 goals" value={p.markets.over_2_5} className="rounded-xl border bg-card p-4" />
        <Meter label="Both teams score" value={p.markets.btts_yes} className="rounded-xl border bg-card p-4" />
        <Meter label={`${p.home_team} clean sheet`} value={p.markets.home_clean_sheet} className="rounded-xl border bg-card p-4" />
        <Meter label={`${p.away_team} clean sheet`} value={p.markets.away_clean_sheet} color="var(--series-away)" className="rounded-xl border bg-card p-4" />
      </div>
      <Tabs defaultValue="overview">
        <div className="overflow-x-auto scrollbar-thin">
          <TabsList className="h-10">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="markets">Goal markets</TabsTrigger>
            <TabsTrigger value="scores">Scorelines</TabsTrigger>
            <TabsTrigger value="models">Models</TabsTrigger>
            <TabsTrigger value="form">Form & H2H</TabsTrigger>
            <TabsTrigger value="availability">
              Availability
              {(p.availability.home.players.length + p.availability.away.players.length) > 0 && (
                <Badge variant="secondary" className="ml-1.5 h-4 px-1 text-[10px]">{p.availability.home.players.length + p.availability.away.players.length}</Badge>
              )}
            </TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="overview" className="mt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Factors p={p} />
            <Panel title="Key numbers">
              <div className="divide-y">
                <MarketRow label={`${p.home_team} win`} value={p.probabilities.home_win} />
                <MarketRow label="Draw" value={p.probabilities.draw} />
                <MarketRow label={`${p.away_team} win`} value={p.probabilities.away_win} />
                <MarketRow label="Over 1.5 goals" value={p.markets.over_1_5} />
                <MarketRow label="Over 3.5 goals" value={p.markets.over_3_5} />
                <MarketRow label={`Correct score ${p.predicted_score}`} value={p.scorelines[0].prob} />
              </div>
            </Panel>
          </div>
        </TabsContent>
        <TabsContent value="markets" className="mt-4"><Markets p={p} /></TabsContent>
        <TabsContent value="scores" className="mt-4"><Scorelines p={p} /></TabsContent>
        <TabsContent value="models" className="mt-4"><Models p={p} /></TabsContent>
        <TabsContent value="form" className="mt-4"><FormH2H p={p} /></TabsContent>
        <TabsContent value="availability" className="mt-4"><Availability p={p} /></TabsContent>
      </Tabs>
      <p className="text-center text-[11px] text-muted-foreground">
        Probabilities are model estimates for analysis and entertainment, not betting advice.
      </p>
    </div>
  );
}

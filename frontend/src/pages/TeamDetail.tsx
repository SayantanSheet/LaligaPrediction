import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Line, LineChart, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { Flame, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/api/client";
import type { SplitStats } from "@/api/types";
import { PageHeader, Panel, StatTile } from "@/components/common/Panel";
import { PlayerAvatar, TeamCrest } from "@/components/common/Crest";
import { FormPills } from "@/components/common/Form";
import { TeamPicker } from "@/components/common/Pickers";
import { ProbabilityBar } from "@/components/common/Probability";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { axisProps, ChartTooltip, gridProps, Legend } from "@/components/charts/ChartBits";
import { useTeamAnalysis } from "@/hooks/queries";
import { dayMonth, pct, seasonLabel, shortDate } from "@/lib/format";
import { cn } from "@/lib/utils";

function SplitCompare({ home, away }: { home: SplitStats; away: SplitStats }) {
  const rows = [
    { metric: "Points / game", home: home.ppg ?? 0, away: away.ppg ?? 0 },
    { metric: "Scored / game", home: home.avg_scored ?? 0, away: away.avg_scored ?? 0 },
    { metric: "Conceded / game", home: home.avg_conceded ?? 0, away: away.avg_conceded ?? 0 },
  ];
  const rates = [
    { metric: "Win rate", home: (home.win_rate ?? 0) * 100, away: (away.win_rate ?? 0) * 100 },
    { metric: "Clean sheets", home: ((home.clean_sheets ?? 0) / Math.max(1, home.played)) * 100, away: ((away.clean_sheets ?? 0) / Math.max(1, away.played)) * 100 },
    { metric: "BTTS", home: (home.btts_rate ?? 0) * 100, away: (away.btts_rate ?? 0) * 100 },
    { metric: "Over 2.5", home: (home.over_2_5_rate ?? 0) * 100, away: (away.over_2_5_rate ?? 0) * 100 },
  ];
  return (
    <Panel title="Home vs. away" subtitle={`${home.played} home · ${away.played} away matches`}>
      <Legend className="mb-3" items={[{ label: "Home", color: "var(--series-home)" }, { label: "Away", color: "var(--series-away)" }]} />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-52">
          <ResponsiveContainer>
            <BarChart data={rows} margin={{ top: 8, right: 4, left: -24, bottom: 0 }} barGap={2}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="metric" {...axisProps} interval={0} tick={{ ...axisProps.tick, fontSize: 10 }} />
              <YAxis {...axisProps} />
              <RTooltip cursor={{ fill: "var(--chart-grid)", opacity: 0.4 }} content={<ChartTooltip formatter={(v) => Number(v).toFixed(2)} />} />
              <Bar dataKey="home" name="Home" fill="var(--series-home)" radius={[4, 4, 0, 0]} maxBarSize={24} />
              <Bar dataKey="away" name="Away" fill="var(--series-away)" radius={[4, 4, 0, 0]} maxBarSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="h-52">
          <ResponsiveContainer>
            <BarChart data={rates} margin={{ top: 8, right: 4, left: -24, bottom: 0 }} barGap={2}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="metric" {...axisProps} interval={0} tick={{ ...axisProps.tick, fontSize: 10 }} />
              <YAxis {...axisProps} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
              <RTooltip cursor={{ fill: "var(--chart-grid)", opacity: 0.4 }} content={<ChartTooltip formatter={(v) => pct(Number(v), 0)} />} />
              <Bar dataKey="home" name="Home" fill="var(--series-home)" radius={[4, 4, 0, 0]} maxBarSize={24} />
              <Bar dataKey="away" name="Away" fill="var(--series-away)" radius={[4, 4, 0, 0]} maxBarSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-muted-foreground"><tr><th className="py-1 text-left font-medium" />{["P", "W", "D", "L", "GF", "GA", "Pts"].map((h) => <th key={h} className="py-1 text-right font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {[["Home", home], ["Away", away]].map(([l, s]) => {
              const x = s as SplitStats;
              return (
                <tr key={l as string} className="border-t">
                  <td className="py-1.5 font-medium">{l as string}</td>
                  {[x.played, x.won, x.drawn, x.lost, x.goals_for, x.goals_against, x.points].map((v, i) => <td key={i} className="py-1.5 text-right tabular">{v}</td>)}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function H2HExplorer({ team }: { team: string }) {
  const [opp, setOpp] = useState<string | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ["h2h", team, opp], queryFn: () => api.h2h(team, opp!), enabled: !!opp });
  return (
    <Panel title="Head-to-head explorer" subtitle="Record against any opponent in the data set">
      <TeamPicker value={opp} onChange={setOpp} exclude={team} placeholder="Choose opponent" />
      <div className="mt-4">
        {!opp ? <EmptyState title="Pick an opponent" /> : isLoading || !data ? <LoadingBlock rows={3} /> : data.played === 0 ? <EmptyState title="No meetings in the data set" /> : (
          <>
            <ProbabilityBar home={data.team_a_wins} draw={data.draws} away={data.team_b_wins} homeLabel={`${team} wins`} awayLabel={`${opp} wins`} showLegend={false} />
            <div className="mt-3 grid grid-cols-3 text-center">
              <div><div className="text-xl font-semibold tabular">{data.team_a_wins}</div><div className="text-[11px] text-muted-foreground">{team}</div></div>
              <div><div className="text-xl font-semibold tabular">{data.draws}</div><div className="text-[11px] text-muted-foreground">Draws</div></div>
              <div><div className="text-xl font-semibold tabular">{data.team_b_wins}</div><div className="text-[11px] text-muted-foreground">{opp}</div></div>
            </div>
            <ul className="mt-3 divide-y text-sm">
              {data.meetings.map((m) => (
                <li key={m.date} className="flex items-center gap-2 py-1.5">
                  <span className="w-24 text-xs text-muted-foreground">{shortDate(m.date)}</span>
                  <span className="min-w-0 flex-1 truncate">{m.home_team} <b className="font-mono tabular">{m.home_score}-{m.away_score}</b> {m.away_team}</span>
                </li>
              ))}
            </ul>
            <Button asChild variant="outline" size="sm" className="mt-3 w-full">
              <Link to={`/predict?home=${encodeURIComponent(team)}&away=${encodeURIComponent(opp)}`}><Target className="mr-1.5 h-3.5 w-3.5" /> Predict {team} vs {opp}</Link>
            </Button>
          </>
        )}
      </div>
    </Panel>
  );
}

export default function TeamDetail() {
  const { team = "" } = useParams();
  const { data: t, isLoading, error, refetch } = useTeamAnalysis(team);
  if (isLoading) return <LoadingBlock rows={8} />;
  if (error || !t) return <ErrorState error={error ?? new Error("Team not found")} onRetry={refetch} />;
  const o = t.overall;
  const elo = t.elo_history.filter((_, i, arr) => i % 2 === 0 || i === arr.length - 1).map((e) => ({ ...e, label: new Date(`${e.date}T12:00:00Z`).toLocaleDateString(undefined, { month: "short", year: "2-digit" }) }));
  const eloMin = elo.length ? Math.floor(Math.min(...elo.map((e) => e.elo)) / 50) * 50 : 1400;
  const eloMax = elo.length ? Math.ceil(Math.max(...elo.map((e) => e.elo)) / 50) * 50 : 1700;
  const streakLabel = t.streak.type === "W" ? "winning" : t.streak.type === "D" ? "drawing" : "losing";
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <TeamCrest team={t.team} logo={t.meta.logo} size="xl" />
        <div className="min-w-0 flex-1">
          <PageHeader eyebrow={`Season ${seasonLabel(t.season)}${t.meta.venue ? ` · ${t.meta.venue}` : ""}`} title={t.team}
            description={t.position ? `${t.position.rank}${["st", "nd", "rd"][t.position.rank - 1] ?? "th"} place · ${t.position.points} points · Elo ${Math.round(t.elo ?? 0)}` : undefined}
            actions={<FormPills form={t.form_string} size="md" />} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <StatTile label="Record" value={`${o.won}-${o.drawn}-${o.lost}`} sub={`${o.played} matches`} />
        <StatTile label="Points / game" value={o.ppg?.toFixed(2)} sub={`${o.points} points`} />
        <StatTile label="Goals" value={`${o.goals_for}:${o.goals_against}`} sub={`${o.avg_scored} scored · ${o.avg_conceded} conceded per game`} />
        <StatTile label="Clean sheets" value={o.clean_sheets} sub={`Failed to score ${o.failed_to_score}×`} />
        <StatTile label="Over 2.5 / BTTS" value={`${pct((o.over_2_5_rate ?? 0) * 100, 0)}`} sub={`BTTS in ${pct((o.btts_rate ?? 0) * 100, 0)} of matches`} />
        <StatTile label="Current streak" icon={<Flame className="h-4 w-4" />} value={`${t.streak.length} ${t.streak.type ?? ""}`} sub={`${t.streak.length}-match ${streakLabel} run`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Goal trend" subtitle="5-match rolling average of goals scored and conceded">
          <Legend className="mb-2" items={[{ label: "Scored", color: "var(--series-home)" }, { label: "Conceded", color: "var(--series-away)" }]} />
          <div className="h-60">
            <ResponsiveContainer>
              <ComposedChart data={t.trend} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="match" {...axisProps} />
                <YAxis {...axisProps} />
                <RTooltip content={<ChartTooltip labelFormatter={(l, p) => `Match ${l} · vs ${(p?.[0]?.payload as { opponent?: string })?.opponent ?? ""}`} />} />
                <Area type="monotone" dataKey="roll_gf" name="Scored" stroke="var(--series-home)" fill="var(--series-home)" fillOpacity={0.1} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="roll_ga" name="Conceded" stroke="var(--series-away)" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Elo rating" subtitle="Strength rating after every match (all seasons)">
          <div className="h-[268px]">
            <ResponsiveContainer>
              <LineChart data={elo} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="label" {...axisProps} minTickGap={40} />
                <YAxis {...axisProps} domain={[eloMin, eloMax]} ticks={Array.from({ length: (eloMax - eloMin) / 50 + 1 }, (_, i) => eloMin + i * 50)} />
                <RTooltip content={<ChartTooltip formatter={(v) => Math.round(Number(v))} labelFormatter={(_, p) => shortDate((p?.[0]?.payload as { date?: string })?.date)} />} />
                <Line type="monotone" dataKey="elo" name="Elo" stroke="var(--series-home)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2"><SplitCompare home={t.home} away={t.away} /></div>
        <Panel title="By half" subtitle="Goals for / against by half">
          {t.halves.first_half_for === undefined ? <EmptyState title="No half-time data" /> : (
            <div className="space-y-4 text-sm">
              {[["1st half", t.halves.first_half_for!, t.halves.first_half_against!], ["2nd half", t.halves.second_half_for!, t.halves.second_half_against!]].map(([l, f, a]) => (
                <div key={l as string}>
                  <div className="mb-1 flex justify-between"><span className="text-muted-foreground">{l}</span><span className="tabular"><b>{f}</b> for · <b>{a}</b> against</span></div>
                  <div className="flex h-2 gap-[2px] overflow-hidden rounded-full">
                    <div style={{ width: `${((f as number) / ((f as number) + (a as number) || 1)) * 100}%`, background: "var(--series-home)" }} />
                    <div style={{ flex: 1, background: "var(--series-away)" }} />
                  </div>
                </div>
              ))}
              <div className="grid grid-cols-3 gap-2 pt-2 text-center">
                <div className="rounded-lg bg-muted/50 py-2"><div className="text-lg font-semibold tabular">{t.halves.leading_at_ht}</div><div className="text-[11px] text-muted-foreground">Led at HT</div></div>
                <div className="rounded-lg bg-muted/50 py-2"><div className="text-lg font-semibold tabular">{t.halves.comebacks}</div><div className="text-[11px] text-muted-foreground">Comebacks</div></div>
                <div className="rounded-lg bg-muted/50 py-2"><div className="text-lg font-semibold tabular">{t.halves.points_dropped_from_winning}</div><div className="text-[11px] text-muted-foreground">Leads lost</div></div>
              </div>
              <Legend items={[{ label: "For", color: "var(--series-home)" }, { label: "Against", color: "var(--series-away)" }]} />
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="Last 10 matches">
          <ul className="divide-y text-sm">
            {t.form.map((f) => (
              <li key={f.date} className="flex items-center gap-2 py-2">
                <FormPills form={f.result} />
                <span className="min-w-0 flex-1 truncate">{f.venue === "home" ? "vs" : "@"} {f.opponent}</span>
                <span className="font-mono tabular">{f.score}</span>
                <span className="w-14 text-right text-xs text-muted-foreground">{dayMonth(f.date)}</span>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Squad" subtitle="Sorted by minutes played" bodyClassName="px-2 pb-3 pt-1">
          <div className="max-h-[420px] overflow-y-auto scrollbar-thin">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-card text-[11px] text-muted-foreground">
                <tr><th className="px-2 py-1.5 text-left font-medium">Player</th><th className="py-1.5 text-right font-medium">Min</th><th className="py-1.5 text-right font-medium">G</th><th className="py-1.5 text-right font-medium">A</th><th className="px-2 py-1.5 text-right font-medium">Rtg</th></tr>
              </thead>
              <tbody>
                {t.squad.map((p) => {
                  const inj = t.injuries.find((i) => i.player_id === p.id);
                  return (
                    <tr key={p.id} className="border-t">
                      <td className="px-2 py-1.5">
                        <Link to={`/players/${p.id}`} className="flex items-center gap-2 hover:underline">
                          <PlayerAvatar name={p.name} photo={p.photo} size="xs" />
                          <span className="truncate">{p.name}</span>
                          {inj && <span className={cn("h-1.5 w-1.5 rounded-full", inj.status === "Out" ? "bg-critical" : "bg-warning")} title={`${inj.status}: ${inj.reason}`} />}
                        </Link>
                      </td>
                      <td className="py-1.5 text-right text-muted-foreground tabular">{p.minutes}</td>
                      <td className="py-1.5 text-right tabular">{p.goals}</td>
                      <td className="py-1.5 text-right tabular">{p.assists}</td>
                      <td className="px-2 py-1.5 text-right tabular">{p.rating?.toFixed(2) ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>
        <div className="space-y-6">
          <Panel title="Unavailable players" subtitle={t.injuries.length ? `Attack at ${pct(t.availability_impact.attack_multiplier * 100, 0)} of full strength` : undefined}>
            {t.injuries.length === 0 ? <EmptyState title="Full squad available" /> : (
              <ul className="space-y-2">
                {t.injuries.map((i) => (
                  <li key={i.player_id} className="flex items-center gap-2 text-sm">
                    <Link to={`/players/${i.player_id}`} className="min-w-0 flex-1 truncate hover:underline">{i.player}</Link>
                    <span className="hidden truncate text-xs text-muted-foreground sm:inline">{i.reason}</span>
                    <StatusChip status={i.status} />
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <H2HExplorer team={t.team} />
        </div>
      </div>
    </div>
  );
}

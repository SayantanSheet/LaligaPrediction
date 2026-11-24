import { Link, useParams } from "react-router-dom";
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { GitCompareArrows } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, StatTile } from "@/components/common/Panel";
import { PlayerAvatar, TeamCrest } from "@/components/common/Crest";
import { PercentileBars } from "@/components/common/PercentileBars";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { axisProps, ChartTooltip, gridProps, Legend } from "@/components/charts/ChartBits";
import { usePlayer } from "@/hooks/queries";
import { dayMonth, num, pct, seasonLabel, shortDate } from "@/lib/format";

export default function PlayerDetail() {
  const { id } = useParams();
  const { data: p, isLoading, error, refetch } = usePlayer(Number(id));
  if (isLoading) return <LoadingBlock rows={8} />;
  if (error || !p) return <ErrorState error={error ?? new Error("Player not found")} onRetry={refetch} />;
  const recent = [...p.recent].reverse().map((r) => ({ ...r, label: `${dayMonth(r.date)} ${r.home ? "vs" : "@"} ${r.opponent}`, ga: r.goals + r.assists }));
  const keeper = p.position === "Goalkeeper";
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <PlayerAvatar name={p.name} photo={p.photo} size="xl" />
        <div className="min-w-0 flex-1">
          <PageHeader
            eyebrow={<span className="inline-flex items-center gap-1.5"><TeamCrest team={p.team} logo={p.team_logo} size="xs" /> <Link to={`/teams/${encodeURIComponent(p.team)}`} className="hover:underline">{p.team}</Link> · {p.position}</span>}
            title={p.name}
            description={[p.firstname && p.lastname ? `${p.firstname} ${p.lastname}` : null, p.age ? `${p.age} years` : null, p.nationality, p.height].filter(Boolean).join(" · ")}
            actions={
              <>
                {p.availability && <StatusChip status={p.availability.status} />}
                <Button asChild variant="outline" size="sm"><Link to={`/compare?a=${p.id}`}><GitCompareArrows className="mr-1.5 h-3.5 w-3.5" /> Compare</Link></Button>
              </>
            } />
        </div>
      </div>

      {p.availability && (
        <div className="rounded-xl border bg-muted/40 p-3 text-sm">
          <b>{p.availability.status}</b>: {p.availability.reason} · missed {p.availability.matches_missed} match{p.availability.matches_missed === 1 ? "" : "es"} since {shortDate(p.availability.since)}
          {p.availability.expected_return && <> · estimated return {shortDate(p.availability.expected_return)}</>}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <StatTile label="Appearances" value={p.appearances} sub={`${p.lineups} starts · ${num(p.minutes)} min`} />
        {keeper ? (
          <>
            <StatTile label="Saves" value={p.saves} sub={`${p.conceded} conceded`} />
            <StatTile label="Goals conceded / 90" value={(90 * p.conceded / Math.max(1, p.minutes)).toFixed(2)} />
          </>
        ) : (
          <>
            <StatTile label="Goals" value={p.goals} sub={p.minutes_per_goal ? `Every ${p.minutes_per_goal} min` : "—"} />
            <StatTile label="Assists" value={p.assists} sub={`${p.key_passes} key passes`} />
          </>
        )}
        <StatTile label="Average rating" value={p.rating?.toFixed(2) ?? "—"} sub={`Season ${seasonLabel(p.season)}`} />
        <StatTile label="Shots" value={`${p.shots_on}/${p.shots}`} sub={p.conversion_rate !== null ? `${pct(p.conversion_rate * 100, 0)} conversion` : "on target / total"} />
        <StatTile label="Discipline" value={`${p.yellow} Y · ${p.red} R`} sub={`${p.fouls_committed} fouls · ${p.fouls_drawn} drawn`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Panel title="Percentile rank" subtitle={`Per 90 minutes vs. ${p.percentile_pool}`} className="lg:col-span-2">
          <PercentileBars percentiles={p.percentiles} per90={p.per90} />
        </Panel>
        <div className="space-y-6 lg:col-span-3">
          <Panel title="Recent matches" subtitle="Match rating with goals + assists">
            {recent.length === 0 ? <EmptyState title="No per-match data for this player">Match logs cover the final rounds of the season.</EmptyState> : (
              <>
                <Legend className="mb-2" items={[{ label: "Goals + assists", color: "var(--series-3)" }, { label: "Rating", color: "var(--series-home)" }]} />
                <div className="h-56">
                  <ResponsiveContainer>
                    <ComposedChart data={recent} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                      <CartesianGrid {...gridProps} />
                      <XAxis dataKey="label" {...axisProps} tick={{ ...axisProps.tick, fontSize: 10 }} interval={0} />
                      <YAxis {...axisProps} domain={[0, 10]} />
                      <RTooltip content={<ChartTooltip />} />
                      <Bar dataKey="ga" name="Goals + assists" fill="var(--series-3)" radius={[4, 4, 0, 0]} maxBarSize={24} />
                      <Line dataKey="rating" name="Rating" stroke="var(--series-home)" strokeWidth={2} dot={{ r: 4, fill: "var(--series-home)", stroke: "var(--chart-surface)", strokeWidth: 2 }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full min-w-[480px] text-sm">
                    <thead className="text-xs text-muted-foreground">
                      <tr><th className="py-1.5 text-left font-medium">Match</th><th className="py-1.5 text-right font-medium">Result</th><th className="py-1.5 text-right font-medium">Min</th><th className="py-1.5 text-right font-medium">G</th><th className="py-1.5 text-right font-medium">A</th><th className="py-1.5 text-right font-medium">Shots</th><th className="py-1.5 text-right font-medium">Rating</th></tr>
                    </thead>
                    <tbody>
                      {p.recent.map((r) => (
                        <tr key={r.fixture_id} className="border-t">
                          <td className="py-1.5">{shortDate(r.date)} · {r.home ? "vs" : "@"} {r.opponent}</td>
                          <td className="py-1.5 text-right font-mono tabular">{r.score}</td>
                          <td className="py-1.5 text-right tabular">{r.minutes}</td>
                          <td className="py-1.5 text-right tabular">{r.goals}</td>
                          <td className="py-1.5 text-right tabular">{r.assists}</td>
                          <td className="py-1.5 text-right tabular">{r.shots}</td>
                          <td className="py-1.5 text-right font-semibold tabular">{r.rating?.toFixed(1) ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </Panel>
          <Panel title="Efficiency">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                ["Shot accuracy", p.shot_accuracy],
                ["Conversion", p.conversion_rate],
                ["Dribble success", p.dribble_success],
                ["Duels won", p.duel_success],
              ].map(([l, v]) => (
                <div key={l as string} className="rounded-lg bg-muted/50 p-3 text-center">
                  <div className="text-lg font-semibold tabular">{v === null ? "—" : pct((v as number) * 100, 0)}</div>
                  <div className="text-[11px] text-muted-foreground">{l as string}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4 text-center">
              <div className="rounded-lg bg-muted/50 p-3"><div className="text-lg font-semibold tabular">{p.pass_accuracy ?? "—"}{p.pass_accuracy ? "%" : ""}</div><div className="text-[11px] text-muted-foreground">Pass accuracy</div></div>
              <div className="rounded-lg bg-muted/50 p-3"><div className="text-lg font-semibold tabular">{p.tackles}</div><div className="text-[11px] text-muted-foreground">Tackles</div></div>
              <div className="rounded-lg bg-muted/50 p-3"><div className="text-lg font-semibold tabular">{p.interceptions}</div><div className="text-[11px] text-muted-foreground">Interceptions</div></div>
              <div className="rounded-lg bg-muted/50 p-3"><div className="text-lg font-semibold tabular">{pct(p.share_of_team_goals * 100, 0)}</div><div className="text-[11px] text-muted-foreground">Share of team goals</div></div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

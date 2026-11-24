import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { Info } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader, Panel, StatTile } from "@/components/common/Panel";
import { PlayerAvatar, TeamCrest } from "@/components/common/Crest";
import { StatusChip } from "@/components/common/StatusChip";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { axisProps, ChartTooltip, gridProps } from "@/components/charts/ChartBits";
import { useInjuries } from "@/hooks/queries";
import type { InjuryEntry } from "@/api/types";
import { pct, shortDate } from "@/lib/format";

function daysBetween(a: string, b: string) {
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / 86400000);
}

export default function Injuries() {
  const { data, isLoading, error, refetch } = useInjuries();
  const [status, setStatus] = useState("all");
  const [team, setTeam] = useState("all");

  const grouped = useMemo(() => {
    const m = new Map<string, InjuryEntry[]>();
    (data?.current ?? [])
      .filter((e) => (status === "all" || e.status === status) && (team === "all" || e.team === team))
      .forEach((e) => m.set(e.team, [...(m.get(e.team) ?? []), e]));
    return [...m.entries()].sort((a, b) => b[1].length - a[1].length);
  }, [data, status, team]);

  if (isLoading) return <LoadingBlock rows={8} />;
  if (error || !data) return <ErrorState error={error} onRetry={refetch} />;
  const s = data.summary;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Availability" title="Injury & availability tracker"
        description={`Who is injured, suspended or doubtful, how long they have been out and when they are expected back. As of ${shortDate(data.as_of)}.`} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Unavailable players" value={s.total} sub={`${s.by_team.length} teams affected`} />
        <StatTile label="Injured" value={s.out} />
        <StatTile label="Suspended" value={s.suspended} />
        <StatTile label="Doubtful" value={s.doubtful} />
      </div>

      <div className="flex items-start gap-2 rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {data.note}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Absences by team">
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={s.by_team.slice(0, 12)} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="team" {...axisProps} interval={0} angle={-35} textAnchor="end" height={70} tick={{ ...axisProps.tick, fontSize: 10 }} />
                <YAxis {...axisProps} allowDecimals={false} />
                <RTooltip cursor={{ fill: "var(--chart-grid)", opacity: 0.4 }} content={<ChartTooltip />} />
                <Bar dataKey="count" name="Unavailable" fill="var(--seq-500)" radius={[4, 4, 0, 0]} maxBarSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Most common injuries this season" subtitle="Missed-match records by injury type">
          <ul className="space-y-2">
            {s.top_reasons.map((r) => (
              <li key={r.reason} className="grid grid-cols-[8rem_1fr_3rem] items-center gap-3 text-sm">
                <span className="truncate text-muted-foreground">{r.reason}</span>
                <div className="h-2 rounded-full bg-muted"><div className="h-full rounded-full" style={{ width: `${(r.count / s.top_reasons[0].count) * 100}%`, background: "var(--seq-500)" }} /></div>
                <span className="text-right tabular">{r.count}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-40" aria-label="Status"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {["Out", "Suspended", "Doubtful", "Unavailable"].map((x) => <SelectItem key={x} value={x}>{x}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={team} onValueChange={setTeam}>
          <SelectTrigger className="w-48" aria-label="Team"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All teams</SelectItem>
            {s.by_team.map((t) => <SelectItem key={t.team} value={t.team}>{t.team} ({t.count})</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {grouped.length === 0 ? <EmptyState title="No players match these filters" /> : (
        <div className="grid gap-4 lg:grid-cols-2">
          {grouped.map(([t, rows]) => {
            const imp = data.impact[t];
            return (
              <Panel key={t} bodyClassName="px-4 pb-3 pt-1"
                title={<Link to={`/teams/${encodeURIComponent(t)}`} className="flex items-center gap-2 hover:underline"><TeamCrest team={t} logo={rows[0].team_logo} size="xs" /> {t}</Link>}
                subtitle={imp ? `Expected attacking output ${pct(imp.attack_multiplier * 100, 0)} of full strength` : undefined}
                action={<span className="text-xs text-muted-foreground">{rows.length} player{rows.length > 1 ? "s" : ""}</span>}>
                <ul className="divide-y">
                  {rows.map((e) => {
                    const toGo = e.expected_return ? daysBetween(data.as_of, e.expected_return) : null;
                    return (
                      <li key={e.player_id} className="flex items-center gap-3 py-2.5">
                        <PlayerAvatar name={e.player} photo={e.photo} size="md" />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-x-2">
                            <Link to={`/players/${e.player_id}`} className="truncate text-sm font-medium hover:underline">{e.player}</Link>
                            {e.position && <span className="text-[11px] text-muted-foreground">{e.position}</span>}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {e.reason} · out since {shortDate(e.since)} · {e.matches_missed} match{e.matches_missed === 1 ? "" : "es"} missed
                            {(e.goals || e.assists) ? ` · ${e.goals}G ${e.assists}A` : ""}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <StatusChip status={e.status} />
                          {e.expected_return && (
                            <span className="text-[11px] text-muted-foreground" title="Estimated from typical recovery time">
                              ~{shortDate(e.expected_return)}{toGo !== null && toGo > 0 ? ` (${toGo}d)` : ""}
                            </span>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </Panel>
            );
          })}
        </div>
      )}
    </div>
  );
}

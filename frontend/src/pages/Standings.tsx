import { Link, useSearchParams } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader, Panel } from "@/components/common/Panel";
import { TeamCrest } from "@/components/common/Crest";
import { FormPills } from "@/components/common/Form";
import { ErrorState, LoadingBlock } from "@/components/common/States";
import { Legend } from "@/components/charts/ChartBits";
import { usePowerRankings, useStandings } from "@/hooks/queries";
import { seasonLabel } from "@/lib/format";
import { useState } from "react";

const zones = [
  { key: "champions_league", label: "Champions League", color: "var(--series-home)" },
  { key: "europa_league", label: "Europa League", color: "var(--series-3)" },
  { key: "conference_league", label: "Conference League", color: "var(--series-4)" },
  { key: "relegation", label: "Relegation", color: "var(--critical)" },
];

function Table({ season }: { season?: number }) {
  const { data, isLoading, error, refetch } = useStandings(season);
  if (isLoading) return <LoadingBlock rows={10} />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  return (
    <Panel bodyClassName="p-0">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="border-b bg-muted/40 text-xs text-muted-foreground">
            <tr>
              <th className="w-12 px-3 py-2.5 text-left font-medium">#</th>
              <th className="px-3 py-2.5 text-left font-medium">Team</th>
              {["P", "W", "D", "L", "GF", "GA", "GD"].map((h) => <th key={h} className="px-2 py-2.5 text-right font-medium">{h}</th>)}
              <th className="px-3 py-2.5 text-right font-medium">Pts</th>
              <th className="hidden px-3 py-2.5 text-right font-medium md:table-cell">Home / Away</th>
              <th className="px-3 py-2.5 text-left font-medium">Form</th>
            </tr>
          </thead>
          <tbody>
            {data!.table.map((r) => {
              const z = zones.find((z) => z.key === r.zone);
              return (
                <tr key={r.team} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-3 py-2">
                    <span className="flex items-center gap-2 tabular">
                      <span className="h-5 w-1 rounded-full" style={{ background: z?.color ?? "transparent" }} title={z?.label} aria-hidden />
                      {r.rank}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <Link to={`/teams/${encodeURIComponent(r.team)}`} className="flex items-center gap-2.5 font-medium hover:underline">
                      <TeamCrest team={r.team} logo={r.logo} size="xs" /> {r.team}
                    </Link>
                  </td>
                  {[r.played, r.won, r.drawn, r.lost, r.goals_for, r.goals_against].map((v, i) => (
                    <td key={i} className="px-2 py-2 text-right text-muted-foreground tabular">{v}</td>
                  ))}
                  <td className="px-2 py-2 text-right tabular">{r.goal_diff > 0 ? `+${r.goal_diff}` : r.goal_diff}</td>
                  <td className="px-3 py-2 text-right font-bold tabular">{r.points}</td>
                  <td className="hidden px-3 py-2 text-right text-xs text-muted-foreground tabular md:table-cell">{r.home_points} / {r.away_points}</td>
                  <td className="px-3 py-2"><FormPills form={r.form} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="border-t px-4 py-3"><Legend items={zones.map((z) => ({ label: z.label, color: z.color }))} /></div>
    </Panel>
  );
}

function Power() {
  const { data, isLoading, error, refetch } = usePowerRankings();
  if (isLoading) return <LoadingBlock rows={10} />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  const items = data!.items;
  const maxA = Math.max(...items.map((i) => i.attack));
  const maxD = Math.max(...items.map((i) => 1 / i.defence));
  return (
    <Panel title="Model power rankings" subtitle="Elo rating plus Dixon-Coles attack and defence strength (1.00 = league average)" bodyClassName="p-0">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="border-b bg-muted/40 text-xs text-muted-foreground">
            <tr>
              <th className="w-10 px-3 py-2.5 text-left font-medium">#</th>
              <th className="px-3 py-2.5 text-left font-medium">Team</th>
              <th className="px-3 py-2.5 text-right font-medium">Elo</th>
              <th className="px-3 py-2.5 text-left font-medium">Attack</th>
              <th className="px-3 py-2.5 text-left font-medium">Defence</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.team} className="border-b last:border-0 hover:bg-muted/30">
                <td className="px-3 py-2 tabular">{r.rank}</td>
                <td className="px-3 py-2">
                  <Link to={`/teams/${encodeURIComponent(r.team)}`} className="flex items-center gap-2.5 font-medium hover:underline">
                    <TeamCrest team={r.team} logo={r.logo} size="xs" /> {r.team}
                  </Link>
                </td>
                <td className="px-3 py-2 text-right font-semibold tabular">{Math.round(r.elo)}</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-28 rounded-full bg-muted"><div className="h-full rounded-full" style={{ width: `${(r.attack / maxA) * 100}%`, background: "var(--series-home)" }} /></div>
                    <span className="text-xs tabular">{r.attack.toFixed(2)}</span>
                  </div>
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-28 rounded-full bg-muted"><div className="h-full rounded-full" style={{ width: `${((1 / r.defence) / maxD) * 100}%`, background: "var(--series-3)" }} /></div>
                    <span className="text-xs tabular" title="Goals conceded multiplier — lower is better">{r.defence.toFixed(2)}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border-t px-4 py-3 text-xs text-muted-foreground">Attack: goals scored vs. an average team. Defence: goals conceded multiplier (lower is better; bar shows strength).</p>
    </Panel>
  );
}

export default function Standings() {
  const [params, setParams] = useSearchParams();
  const { data } = useStandings();
  const [season, setSeason] = useState<number | undefined>(undefined);
  return (
    <div>
      <PageHeader eyebrow="League" title="Standings & power rankings"
        description="League table computed from match results, plus model-based strength ratings."
        actions={data && (
          <Select value={String(season ?? data.season)} onValueChange={(v) => setSeason(Number(v))}>
            <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
            <SelectContent>{data.seasons.map((s) => <SelectItem key={s} value={String(s)}>Season {seasonLabel(s)}</SelectItem>)}</SelectContent>
          </Select>
        )} />
      <Tabs value={params.get("tab") ?? "table"} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList>
          <TabsTrigger value="table">League table</TabsTrigger>
          <TabsTrigger value="power">Power rankings</TabsTrigger>
        </TabsList>
        <TabsContent value="table" className="mt-4"><Table season={season} /></TabsContent>
        <TabsContent value="power" className="mt-4"><Power /></TabsContent>
      </Tabs>
    </div>
  );
}

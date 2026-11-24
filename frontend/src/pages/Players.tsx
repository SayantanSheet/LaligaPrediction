import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader, Panel } from "@/components/common/Panel";
import { PlayerAvatar, TeamCrest } from "@/components/common/Crest";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { useLeaders, usePlayers, useTeams } from "@/hooks/queries";
import type { PlayerSummary } from "@/api/types";
import { seasonLabel } from "@/lib/format";
import { cn } from "@/lib/utils";

const COLS: { key: keyof PlayerSummary; label: string; fmt?: (v: number) => string }[] = [
  { key: "appearances", label: "Apps" },
  { key: "minutes", label: "Min" },
  { key: "goals", label: "G" },
  { key: "assists", label: "A" },
  { key: "ga_per90", label: "G+A/90", fmt: (v) => v.toFixed(2) },
  { key: "shots", label: "Shots" },
  { key: "key_passes", label: "Key P" },
  { key: "rating", label: "Rating", fmt: (v) => v.toFixed(2) },
];

function LeaderCard({ title, rows, fmt }: { title: string; rows: PlayerSummary[]; fmt?: (v: number) => string }) {
  return (
    <Panel title={title} bodyClassName="px-4 pb-4 pt-3">
      <ol className="space-y-2">
        {rows.map((p, i) => (
          <li key={p.id}>
            <Link to={`/players/${p.id}`} className="flex items-center gap-2.5 rounded-md p-0.5 hover:bg-muted/60">
              <span className="w-3 text-xs text-muted-foreground tabular">{i + 1}</span>
              <PlayerAvatar name={p.name} photo={p.photo} size="sm" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{p.name}</span>
                <span className="block truncate text-[11px] text-muted-foreground">{p.team}</span>
              </span>
              <span className="font-semibold tabular">{fmt ? fmt(p.value ?? 0) : p.value}</span>
            </Link>
          </li>
        ))}
      </ol>
    </Panel>
  );
}

export default function Players() {
  const [q, setQ] = useState("");
  const [team, setTeam] = useState("all");
  const [position, setPosition] = useState("all");
  const [minMinutes, setMinMinutes] = useState("450");
  const [sort, setSort] = useState<keyof PlayerSummary>("rating");
  const { data: teams } = useTeams();
  const leaders = useLeaders(5);
  const { data, isLoading, error, refetch } = usePlayers({ min_minutes: 0, limit: 1000, sort: "minutes" });

  const rows = useMemo(() => {
    let r = data?.items ?? [];
    if (team !== "all") r = r.filter((p) => p.team === team);
    if (position !== "all") r = r.filter((p) => p.position === position);
    if (q) r = r.filter((p) => p.name.toLowerCase().includes(q.toLowerCase()));
    r = r.filter((p) => p.minutes >= Number(minMinutes));
    return [...r].sort((a, b) => ((b[sort] as number) ?? -1) - ((a[sort] as number) ?? -1));
  }, [data, team, position, q, minMinutes, sort]);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Players" title="Player performance analytics"
        description={`Goals, assists, ratings and per-90 output for every LaLiga player${data ? ` · season ${seasonLabel(data.season)}` : ""}.`} />

      {leaders.data && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <LeaderCard title="Top scorers" rows={leaders.data.goals} />
          <LeaderCard title="Top assists" rows={leaders.data.assists} />
          <LeaderCard title="Best rated (900+ min)" rows={leaders.data.rating} fmt={(v) => v.toFixed(2)} />
          <LeaderCard title="Goals per 90 (900+ min)" rows={leaders.data.goals_per90} fmt={(v) => v.toFixed(2)} />
        </div>
      )}

      <Panel bodyClassName="p-0">
        {/* Filters: one row above the table */}
        <div className="flex flex-wrap items-center gap-2 border-b p-3">
          <div className="relative min-w-[200px] flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search player…" className="pl-8" aria-label="Search player" />
          </div>
          <Select value={team} onValueChange={setTeam}>
            <SelectTrigger className="w-44" aria-label="Team"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="all">All teams</SelectItem>{teams?.items.map((t) => <SelectItem key={t.name} value={t.name}>{t.name}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={position} onValueChange={setPosition}>
            <SelectTrigger className="w-36" aria-label="Position"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All positions</SelectItem>
              {["Goalkeeper", "Defender", "Midfielder", "Attacker"].map((p) => <SelectItem key={p} value={p}>{p}s</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={minMinutes} onValueChange={setMinMinutes}>
            <SelectTrigger className="w-36" aria-label="Minimum minutes"><SelectValue /></SelectTrigger>
            <SelectContent>{["0", "450", "900", "1800"].map((m) => <SelectItem key={m} value={m}>{m === "0" ? "Any minutes" : `${m}+ min`}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        {isLoading ? <LoadingBlock rows={10} className="p-4" /> : error ? <ErrorState error={error} onRetry={refetch} className="m-4" /> : rows.length === 0 ? <EmptyState title="No players match these filters" className="m-4" /> : (
          <div className="max-h-[70vh] overflow-auto scrollbar-thin">
            <table className="w-full min-w-[820px] text-sm">
              <thead className="sticky top-0 z-10 bg-card text-xs text-muted-foreground shadow-[0_1px_0_hsl(var(--border))]">
                <tr>
                  <th className="w-10 px-3 py-2.5 text-left font-medium">#</th>
                  <th className="px-3 py-2.5 text-left font-medium">Player</th>
                  <th className="px-3 py-2.5 text-left font-medium">Team</th>
                  {COLS.map((c) => (
                    <th key={c.key} className="px-2 py-2.5 text-right font-medium">
                      <button onClick={() => setSort(c.key)} className={cn("inline-flex items-center gap-0.5 hover:text-foreground", sort === c.key && "text-foreground")} aria-label={`Sort by ${c.label}`}>
                        {c.label}{sort === c.key && <ArrowDown className="h-3 w-3" />}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 300).map((p, i) => (
                  <tr key={p.id} className="border-t hover:bg-muted/30">
                    <td className="px-3 py-2 text-xs text-muted-foreground tabular">{i + 1}</td>
                    <td className="px-3 py-2">
                      <Link to={`/players/${p.id}`} className="flex items-center gap-2.5 hover:underline">
                        <PlayerAvatar name={p.name} photo={p.photo} size="sm" />
                        <span className="min-w-0"><span className="block truncate font-medium">{p.name}</span><span className="block text-[11px] text-muted-foreground">{p.position}{p.age ? ` · ${p.age}` : ""}</span></span>
                      </Link>
                    </td>
                    <td className="px-3 py-2"><span className="flex items-center gap-1.5 text-xs text-muted-foreground"><TeamCrest team={p.team} logo={p.team_logo} size="xs" />{p.team}</span></td>
                    {COLS.map((c) => {
                      const v = p[c.key] as number | null;
                      return <td key={c.key} className={cn("px-2 py-2 text-right tabular", sort === c.key ? "font-semibold" : "text-muted-foreground")}>{v === null || v === undefined ? "—" : c.fmt ? c.fmt(v) : v}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length > 300 && <p className="p-3 text-center text-xs text-muted-foreground">Showing the top 300 of {rows.length}. Refine the filters to see more.</p>}
          </div>
        )}
      </Panel>
    </div>
  );
}

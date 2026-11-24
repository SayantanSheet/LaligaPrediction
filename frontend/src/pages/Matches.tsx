import { Radio } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader, Panel } from "@/components/common/Panel";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { TeamCrest } from "@/components/common/Crest";
import { FixtureCard } from "@/components/matches/FixtureCard";
import { useLive, useResults, useSimulatedRound, useUpcoming } from "@/hooks/queries";
import { kickoffTime, shortDate, timeAgo } from "@/lib/format";

function SourceNote({ source, fetchedAt }: { source?: string; fetchedAt?: string | null }) {
  const label = source === "live" ? "Live from API-Football" : source === "cache" ? "Cached API response" : source === "stale-cache" ? "Stale cache (daily API budget reached)" : "API unavailable";
  return <p className="text-xs text-muted-foreground">{label}{fetchedAt ? ` · updated ${timeAgo(fetchedAt)}` : ""}</p>;
}

function Live() {
  const { data, isLoading, error, refetch } = useLive();
  if (isLoading) return <LoadingBlock />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  const rows = data!.matches.length ? data!.matches : data!.today;
  return (
    <div className="space-y-3">
      <SourceNote source={data!.source} fetchedAt={data!.fetched_at} />
      {rows.length === 0 ? (
        <EmptyState icon={<Radio className="h-6 w-6" />} title="No LaLiga matches today">
          Live scores appear here automatically and refresh every minute while a match is in progress.
        </EmptyState>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map((f) => (
            <FixtureCard key={f.id} home={f.home_team} away={f.away_team} homeLogo={f.home_logo} awayLogo={f.away_logo}
              top={`${f.round} · ${f.is_live ? f.status_long : kickoffTime(f.kickoff)}`} live={f.is_live} elapsed={f.elapsed}
              score={{ home: f.home_score, away: f.away_score }} />
          ))}
        </div>
      )}
    </div>
  );
}

function Upcoming() {
  const { data, isLoading, error, refetch } = useUpcoming();
  const sim = useSimulatedRound();
  if (isLoading) return <LoadingBlock />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <SourceNote source={data!.source} fetchedAt={data!.fetched_at} />
        {data!.matches.length === 0 ? (
          <EmptyState title="No LaLiga fixtures in the next 48 hours">{data!.note}</EmptyState>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {data!.matches.map((f) => (
              <FixtureCard key={f.id} home={f.home_team} away={f.away_team} homeLogo={f.home_logo} awayLogo={f.away_logo}
                top={`${f.round} · ${kickoffTime(f.kickoff)}`} prediction={f.prediction} />
            ))}
          </div>
        )}
      </div>
      {sim.data && sim.data.matches.length > 0 && (
        <Panel title="Model matchday simulation" subtitle={sim.data.label}>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {sim.data.matches.map((m) => (
              <FixtureCard key={m.home_team + m.away_team} home={m.home_team} away={m.away_team} homeLogo={m.home_logo} awayLogo={m.away_logo}
                top="Simulated fixture" prediction={m.prediction} />
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}

function Results() {
  const { data, isLoading, error, refetch } = useResults();
  if (isLoading) return <LoadingBlock />;
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  const api = data!.live_api.matches;
  const groups = new Map<string, typeof data.history>();
  data!.history.forEach((r) => {
    const k = `${r.round ?? ""} · ${r.season}/${String(r.season + 1).slice(2)}`;
    groups.set(k, [...(groups.get(k) ?? []), r]);
  });
  return (
    <div className="space-y-6">
      {api.length > 0 && (
        <Panel title="Latest results (API)">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {api.map((f) => (
              <FixtureCard key={f.id} home={f.home_team} away={f.away_team} homeLogo={f.home_logo} awayLogo={f.away_logo}
                top={`${f.round} · ${kickoffTime(f.kickoff)}`} score={{ home: f.home_score, away: f.away_score }} />
            ))}
          </div>
        </Panel>
      )}
      {[...groups.entries()].map(([k, rows]) => (
        <Panel key={k} title={k} subtitle={`Data set results · data to ${shortDate(data!.data_as_of)}`}>
          <ul className="divide-y">
            {rows.map((r) => (
              <li key={r.id} className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 py-2.5 text-sm">
                <span className="flex min-w-0 items-center justify-end gap-2 text-right">
                  <span className={r.home_score > r.away_score ? "truncate font-semibold" : "truncate"}>{r.home_team}</span>
                  <TeamCrest team={r.home_team} logo={r.home_logo} size="xs" />
                </span>
                <span className="flex flex-col items-center">
                  <span className="rounded-md bg-muted px-2 py-0.5 font-mono font-semibold tabular">{r.home_score} – {r.away_score}</span>
                  {r.halftime.home !== null && <span className="text-[10px] text-muted-foreground tabular">HT {r.halftime.home}-{r.halftime.away}</span>}
                </span>
                <span className="flex min-w-0 items-center gap-2">
                  <TeamCrest team={r.away_team} logo={r.away_logo} size="xs" />
                  <span className={r.away_score > r.home_score ? "truncate font-semibold" : "truncate"}>{r.away_team}</span>
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      ))}
    </div>
  );
}

export default function Matches() {
  return (
    <div>
      <PageHeader eyebrow="Fixtures" title="Live & upcoming matches"
        description="Live LaLiga scores and upcoming fixtures from API-Football, each with a model prediction, plus recent results." />
      <Tabs defaultValue="live">
        <TabsList>
          <TabsTrigger value="live">Live</TabsTrigger>
          <TabsTrigger value="upcoming">Upcoming</TabsTrigger>
          <TabsTrigger value="results">Results</TabsTrigger>
        </TabsList>
        <TabsContent value="live" className="mt-4"><Live /></TabsContent>
        <TabsContent value="upcoming" className="mt-4"><Upcoming /></TabsContent>
        <TabsContent value="results" className="mt-4"><Results /></TabsContent>
      </Tabs>
    </div>
  );
}

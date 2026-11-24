import { Link } from "react-router-dom";
import { PageHeader } from "@/components/common/Panel";
import { TeamCrest } from "@/components/common/Crest";
import { FormPills } from "@/components/common/Form";
import { ErrorState, LoadingBlock } from "@/components/common/States";
import { useStandings } from "@/hooks/queries";
import { seasonLabel } from "@/lib/format";

export default function Teams() {
  const { data, isLoading, error, refetch } = useStandings();
  return (
    <div>
      <PageHeader eyebrow="Clubs" title="Team performance"
        description={`Season stats, form, home vs. away splits, Elo trends and head-to-head records${data ? ` · ${seasonLabel(data.season)}` : ""}.`} />
      {isLoading ? <LoadingBlock rows={8} /> : error ? <ErrorState error={error} onRetry={refetch} /> : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {data!.table.map((r) => (
            <Link key={r.team} to={`/teams/${encodeURIComponent(r.team)}`}
              className="group rounded-xl border bg-card p-4 shadow-sm transition-colors hover:border-foreground/20">
              <div className="flex items-center gap-3">
                <TeamCrest team={r.team} logo={r.logo} size="lg" />
                <div className="min-w-0">
                  <div className="truncate font-semibold group-hover:underline">{r.team}</div>
                  <div className="text-xs text-muted-foreground">#{r.rank} · {r.points} pts</div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-3 text-center text-xs">
                <div><div className="text-base font-semibold tabular">{r.won}-{r.drawn}-{r.lost}</div><div className="text-muted-foreground">W-D-L</div></div>
                <div><div className="text-base font-semibold tabular">{r.goals_for}:{r.goals_against}</div><div className="text-muted-foreground">Goals</div></div>
                <div><div className="text-base font-semibold tabular">{(r.points / Math.max(1, r.played)).toFixed(2)}</div><div className="text-muted-foreground">PPG</div></div>
              </div>
              <div className="mt-3 flex justify-center"><FormPills form={r.form} /></div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

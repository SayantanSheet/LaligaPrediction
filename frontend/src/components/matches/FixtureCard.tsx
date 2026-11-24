import { Link } from "react-router-dom";
import { Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { QuickPick } from "@/api/types";
import { TeamCrest } from "@/components/common/Crest";
import { ProbabilityBar } from "@/components/common/Probability";
import { cn } from "@/lib/utils";
import { pct } from "@/lib/format";

export function FixtureCard({ home, away, homeLogo, awayLogo, top, score, live, elapsed, prediction, className }: {
  home: string; away: string; homeLogo?: string | null; awayLogo?: string | null; top?: React.ReactNode;
  score?: { home: number | null; away: number | null } | null; live?: boolean; elapsed?: number | null;
  prediction?: QuickPick | null; className?: string;
}) {
  const hasScore = score && score.home !== null && score.away !== null;
  return (
    <div className={cn("rounded-xl border bg-card p-4 shadow-sm transition-colors hover:border-foreground/20", className)}>
      <div className="mb-3 flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span className="truncate">{top}</span>
        {live && (
          <span className="inline-flex items-center gap-1 rounded-full bg-critical/15 px-2 py-0.5 font-semibold text-critical">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-critical" aria-hidden /> LIVE {elapsed ? `${elapsed}'` : ""}
          </span>
        )}
      </div>
      <div className="space-y-2">
        {[{ t: home, l: homeLogo, s: score?.home }, { t: away, l: awayLogo, s: score?.away }].map((r, i) => (
          <div key={i} className="flex items-center gap-2.5">
            <TeamCrest team={r.t} logo={r.l} size="sm" />
            <Link to={`/teams/${encodeURIComponent(r.t)}`} className="min-w-0 flex-1 truncate text-sm font-medium hover:underline">{r.t}</Link>
            {hasScore && <span className="font-mono text-base font-semibold tabular">{r.s}</span>}
          </div>
        ))}
      </div>
      {prediction && (
        <div className="mt-4 border-t pt-3">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Model: <b className="font-mono text-foreground">{prediction.predicted_score}</b></span>
            <span className="text-muted-foreground">O2.5 <b className="text-foreground tabular">{pct(prediction.over_2_5, 0)}</b> · BTTS <b className="text-foreground tabular">{pct(prediction.btts, 0)}</b></span>
          </div>
          <ProbabilityBar home={prediction.home_win} draw={prediction.draw} away={prediction.away_win} homeLabel="1" awayLabel="2" height="h-2" />
          <Button asChild variant="ghost" size="sm" className="mt-2 h-8 w-full text-xs">
            <Link to={`/predict?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}`}><Target className="mr-1.5 h-3.5 w-3.5" /> Full analysis</Link>
          </Button>
        </div>
      )}
    </div>
  );
}

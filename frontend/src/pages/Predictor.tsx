import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowLeftRight, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/common/Panel";
import { TeamPicker } from "@/components/common/Pickers";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { PredictionView } from "@/components/predict/PredictionView";
import { useHealth, usePredict } from "@/hooks/queries";

export default function Predictor() {
  const [params, setParams] = useSearchParams();
  const [home, setHome] = useState<string | null>(params.get("home"));
  const [away, setAway] = useState<string | null>(params.get("away"));
  const [availability, setAvailability] = useState(true);
  const predict = usePredict();
  const { data: health } = useHealth();
  const ready = health?.model === "ready";
  const autoRan = useRef(false);

  const run = (h = home, a = away, av = availability) => {
    if (!h || !a) return;
    setParams({ home: h, away: a }, { replace: true });
    predict.mutate(
      { home: h, away: a, availability: av },
      { onError: (e) => toast.error("Prediction failed", { description: e instanceof Error ? e.message : String(e) }) },
    );
  };

  // Deep links (/predict?home=…&away=…) run automatically once the model is ready.
  useEffect(() => {
    if (!autoRan.current && ready && home && away) {
      autoRan.current = true;
      run();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  return (
    <div>
      <PageHeader
        eyebrow="Match predictor"
        title="Predict any LaLiga fixture"
        description="Win/draw/loss probabilities, expected goals, goal markets and correct-score odds from a calibrated Poisson + machine-learning ensemble."
      />

      <section className="rounded-2xl border bg-card p-4 shadow-sm md:p-5">
        <div className="grid items-end gap-3 md:grid-cols-[1fr_auto_1fr_auto]">
          <TeamPicker label="Home team" value={home} onChange={setHome} exclude={away} />
          <Button variant="ghost" size="icon" className="mx-auto" aria-label="Swap home and away"
            onClick={() => { setHome(away); setAway(home); }} disabled={!home && !away}>
            <ArrowLeftRight className="h-4 w-4" />
          </Button>
          <TeamPicker label="Away team" value={away} onChange={setAway} exclude={home} />
          <Button size="lg" className="h-14 px-6" disabled={!home || !away || predict.isPending || !ready} onClick={() => run()}>
            {predict.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
            Predict
          </Button>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <Switch id="availability" checked={availability} onCheckedChange={(v) => { setAvailability(v); if (predict.data) run(home, away, v); }} />
          <Label htmlFor="availability" className="text-xs font-normal text-muted-foreground">
            Adjust for injuries & suspensions
          </Label>
        </div>
      </section>

      <div className="mt-6">
        {predict.isPending && <LoadingBlock rows={6} />}
        {predict.isError && !predict.isPending && <ErrorState error={predict.error} onRetry={() => run()} />}
        {predict.data && !predict.isPending && <PredictionView p={predict.data} />}
        {!predict.data && !predict.isPending && !predict.isError && (
          <EmptyState title="Pick two teams to generate a prediction" className="py-16">
            Try a classic: Real Madrid vs Barcelona, or Sevilla vs Real Betis.
          </EmptyState>
        )}
      </div>
    </div>
  );
}

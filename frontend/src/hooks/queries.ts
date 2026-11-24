import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

const HOUR = 60 * 60 * 1000;

export const useHealth = () =>
  useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: (q) => (q.state.data?.model === "ready" ? 5 * 60 * 1000 : 3000),
    retry: 10,
    retryDelay: (n) => Math.min(1000 * 2 ** n, 8000),
  });

export const useTeams = () => useQuery({ queryKey: ["teams"], queryFn: api.teams, staleTime: HOUR });
export const useStandings = (season?: number) =>
  useQuery({ queryKey: ["standings", season], queryFn: () => api.standings(season), staleTime: HOUR });
export const usePowerRankings = () => useQuery({ queryKey: ["power"], queryFn: api.powerRankings, staleTime: HOUR });
export const useTeamAnalysis = (team?: string) =>
  useQuery({ queryKey: ["team", team], queryFn: () => api.teamAnalysis(team!), enabled: !!team, staleTime: HOUR });
export const usePlayers = (p: Parameters<typeof api.players>[0]) =>
  useQuery({ queryKey: ["players", p], queryFn: () => api.players(p), staleTime: HOUR });
export const useLeaders = (limit = 10) => useQuery({ queryKey: ["leaders", limit], queryFn: () => api.leaders(limit), staleTime: HOUR });
export const usePlayer = (id?: number) =>
  useQuery({ queryKey: ["player", id], queryFn: () => api.player(id!), enabled: !!id, staleTime: HOUR });
export const useCompare = (a?: number, b?: number) =>
  useQuery({ queryKey: ["compare", a, b], queryFn: () => api.compare(a!, b!), enabled: !!a && !!b && a !== b, staleTime: HOUR });
export const useInjuries = (team?: string) => useQuery({ queryKey: ["injuries", team], queryFn: () => api.injuries(team), staleTime: HOUR });
export const useLive = () =>
  useQuery({
    queryKey: ["live"],
    queryFn: api.live,
    refetchInterval: (q) => (q.state.data?.polling ? 60_000 : 10 * 60_000),
  });
export const useUpcoming = () => useQuery({ queryKey: ["upcoming"], queryFn: api.upcoming, staleTime: 15 * 60_000 });
export const useResults = () => useQuery({ queryKey: ["results"], queryFn: () => api.results(40), staleTime: 15 * 60_000 });
export const useSimulatedRound = () => useQuery({ queryKey: ["simround"], queryFn: api.simulateRound, staleTime: HOUR });
export const useModelMetrics = () => useQuery({ queryKey: ["metrics"], queryFn: api.modelMetrics, staleTime: HOUR });
export const useHistory = (limit = 50) => useQuery({ queryKey: ["history", limit], queryFn: () => api.history(limit) });

export const usePredict = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { home: string; away: string; availability: boolean }) => api.predict(v.home, v.away, v.availability),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["history"] }),
  });
};

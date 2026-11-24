import type {
  Health, HistoryItem, InjuryTracker, Leaders, LiveFixtures, ModelMetrics, PlayerComparison, PlayerProfile,
  PlayerSummary, PowerRanking, Prediction, Results, SimulatedRound, Standings, TeamAnalysis, TeamItem, UpcomingFixtures,
} from "./types";

export * from "./types";

export const API_BASE_URL: string = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") || "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
  } catch {
    throw new ApiError("Cannot reach the prediction server. It may be waking up — try again in a moment.", 0);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(detail || `Request failed (${res.status})`, res.status);
  }
  return res.json() as Promise<T>;
}

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const s = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  });
  const str = s.toString();
  return str ? `?${str}` : "";
};

export const api = {
  health: () => request<Health>("/health"),
  teams: () => request<{ teams: string[]; items: TeamItem[]; season: number }>("/teams"),
  predict: (home_team: string, away_team: string, use_availability = true) =>
    request<Prediction>("/predict", { method: "POST", body: JSON.stringify({ home_team, away_team, use_availability }) }),
  standings: (season?: number) => request<Standings>(`/standings${qs({ season })}`),
  powerRankings: () => request<{ items: PowerRanking[] }>("/power-rankings"),
  teamAnalysis: (team: string) => request<TeamAnalysis>(`/teams/${encodeURIComponent(team)}/analysis`),
  h2h: (home: string, away: string) => request<Prediction["h2h"]>(`/h2h${qs({ home, away })}`),
  players: (p: { team?: string; position?: string; q?: string; sort?: string; min_minutes?: number; limit?: number } = {}) =>
    request<{ season: number; items: PlayerSummary[] }>(`/players${qs(p)}`),
  leaders: (limit = 10) => request<Leaders>(`/players/leaders${qs({ limit })}`),
  player: (id: number) => request<PlayerProfile>(`/players/${id}`),
  compare: (a: number, b: number) => request<PlayerComparison>(`/players/compare${qs({ a, b })}`),
  injuries: (team?: string) => request<InjuryTracker>(`/injuries${qs({ team })}`),
  live: () => request<LiveFixtures>("/fixtures/live"),
  upcoming: () => request<UpcomingFixtures>("/fixtures/upcoming"),
  results: (limit = 40) => request<Results>(`/fixtures/results${qs({ limit })}`),
  simulateRound: () => request<SimulatedRound>("/fixtures/simulate-round"),
  modelMetrics: () => request<ModelMetrics>("/model/metrics"),
  history: (limit = 50) => request<{ total: number; items: HistoryItem[] }>(`/history${qs({ limit })}`),
};

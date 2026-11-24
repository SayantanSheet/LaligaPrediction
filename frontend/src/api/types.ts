export type Outcome = "H" | "D" | "A";
export type FormResult = "W" | "D" | "L";

export interface Health {
  status: string;
  model: "ready" | "training" | "loading" | "error";
  model_error: string | null;
  data: { matches: number; players: number; data_as_of: string | null; latest_season: number | null; player_season: number | null };
  api_quota: { day: string; used: number; budget: number; remaining: number; configured: boolean };
}

export interface TeamItem {
  name: string;
  logo: string | null;
  id: number | null;
  code?: string | null;
  venue?: string | null;
  elo: number | null;
}

export interface FormEntry {
  date: string;
  opponent: string;
  venue: "home" | "away";
  score: string;
  result: FormResult;
  round?: string | null;
}

export interface SplitStats {
  played: number;
  won?: number;
  drawn?: number;
  lost?: number;
  goals_for?: number;
  goals_against?: number;
  points?: number;
  ppg?: number;
  avg_scored?: number;
  avg_conceded?: number;
  win_rate?: number;
  clean_sheets?: number;
  failed_to_score?: number;
  btts_rate?: number;
  over_1_5_rate?: number;
  over_2_5_rate?: number;
  over_3_5_rate?: number;
}

export interface Probabilities {
  home_win: number;
  draw: number;
  away_win: number;
}

export interface AvailabilityPlayer {
  player: string;
  player_id: number;
  position: string;
  status: string;
  goals: number;
  assists: number;
  impact: number;
}

export interface TeamImpact {
  attack_multiplier: number;
  opponent_attack_multiplier: number;
  players: AvailabilityPlayer[];
}

export interface Factor {
  label: string;
  detail: string;
  direction: "home" | "away" | "neutral";
  weight: number;
}

export interface H2H {
  team_a: string;
  team_b: string;
  played: number;
  team_a_wins: number;
  team_b_wins: number;
  draws: number;
  team_a_goals: number;
  team_b_goals: number;
  avg_goals: number;
  btts_rate: number;
  meetings: {
    date: string;
    season: number;
    home_team: string;
    away_team: string;
    home_score: number;
    away_score: number;
    winner: string | null;
  }[];
}

export interface TeamCard {
  team: string;
  logo: string | null;
  elo: number;
  form: FormEntry[];
  form_string: string;
  season: SplitStats;
  ratings: { team: string; attack: number; defence: number } | null;
  key_players: { id: number; name: string; photo: string | null; position: string; goals: number; assists: number; rating: number | null }[];
  unavailable: AvailabilityPlayer[];
}

export interface Prediction {
  home_team: string;
  away_team: string;
  home_logo: string | null;
  away_logo: string | null;
  probabilities: Probabilities;
  probabilities_without_availability: Probabilities;
  predicted_outcome: Outcome;
  predicted_outcome_label: string;
  predicted_score: string;
  confidence: number;
  confidence_level: "high" | "medium" | "low";
  expected_goals: { home: number; away: number; home_base: number; away_base: number };
  markets: {
    over_0_5: number;
    over_1_5: number;
    over_2_5: number;
    over_3_5: number;
    over_4_5: number;
    under_1_5: number;
    under_2_5: number;
    under_3_5: number;
    btts_yes: number;
    btts_no: number;
    home_clean_sheet: number;
    away_clean_sheet: number;
    home_to_score: number;
    away_to_score: number;
    double_chance_1x: number;
    double_chance_x2: number;
    double_chance_12: number;
    draw_no_bet_home: number;
    total_goals_dist: number[];
    winning_margin: Record<string, number>;
    home_goals_dist: number[];
    away_goals_dist: number[];
  };
  scorelines: { score: string; home: number; away: number; prob: number }[];
  score_matrix: number[][];
  models: ({ key: string; name: string } & Probabilities)[];
  model_agreement: { agreeing_models: number; total_models: number; level: "high" | "medium" | "low"; spread: number };
  availability: { home: TeamImpact; away: TeamImpact; applied: boolean };
  factors: Factor[];
  teams: { home: TeamCard; away: TeamCard };
  h2h: H2H;
  model_version: string;
}

export interface StandingRow {
  rank: number;
  team: string;
  logo: string | null;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  points: number;
  form: string;
  home_points: number;
  away_points: number;
  zone: "champions_league" | "europa_league" | "conference_league" | "relegation" | null;
}

export interface Standings {
  season: number;
  seasons: number[];
  table: StandingRow[];
}

export interface PowerRanking {
  rank: number;
  team: string;
  logo: string | null;
  elo: number;
  attack: number;
  defence: number;
  net_rating: number;
}

export interface PlayerSummary {
  id: number;
  name: string;
  photo: string | null;
  team: string;
  team_logo: string | null;
  position: string;
  age: number | null;
  nationality: string | null;
  appearances: number;
  minutes: number;
  goals: number;
  assists: number;
  rating: number | null;
  shots: number;
  key_passes: number;
  yellow: number;
  red: number;
  ga_per90: number;
  value?: number;
}

export interface PlayerMatch {
  fixture_id: number;
  date: string;
  round: string;
  opponent: string;
  home: boolean;
  score: string;
  minutes: number;
  rating: number | null;
  goals: number;
  assists: number;
  shots: number;
  key_passes: number;
}

export type MetricKey =
  | "goals" | "assists" | "shots" | "shots_on" | "key_passes" | "passes" | "pass_accuracy"
  | "dribbles_won" | "tackles" | "interceptions" | "duels_won" | "fouls_drawn" | "rating";

export interface PlayerProfile extends PlayerSummary {
  firstname: string | null;
  lastname: string | null;
  height: string | null;
  lineups: number;
  captain: boolean;
  shots_on: number;
  passes: number;
  pass_accuracy: number;
  tackles: number;
  blocks: number;
  interceptions: number;
  duels: number;
  duels_won: number;
  dribbles: number;
  dribbles_won: number;
  fouls_drawn: number;
  fouls_committed: number;
  conceded: number;
  saves: number;
  pen_scored: number;
  pen_missed: number;
  per90: Record<MetricKey, number | null>;
  percentiles: Record<MetricKey, number | null>;
  percentile_pool: string;
  share_of_team_goals: number;
  shot_accuracy: number | null;
  conversion_rate: number | null;
  dribble_success: number | null;
  duel_success: number | null;
  minutes_per_goal: number | null;
  recent: PlayerMatch[];
  season: number;
  availability?: InjuryEntry | null;
}

export interface PlayerComparison {
  a: PlayerProfile;
  b: PlayerProfile;
  rows: {
    key: MetricKey;
    label: string;
    a: number | null;
    b: number | null;
    a_total: number | null;
    b_total: number | null;
    better: "a" | "b" | null;
    a_pct: number | null;
    b_pct: number | null;
  }[];
  radar: { metric: string; a: number; b: number }[];
  edge: { a: number; b: number };
}

export interface Leaders {
  season: number;
  goals: PlayerSummary[];
  assists: PlayerSummary[];
  goal_contributions: PlayerSummary[];
  rating: PlayerSummary[];
  key_passes: PlayerSummary[];
  dribbles: PlayerSummary[];
  tackles: PlayerSummary[];
  goals_per90: PlayerSummary[];
}

export type InjuryStatus = "Out" | "Doubtful" | "Suspended" | "Unavailable" | "Available";

export interface InjuryEntry {
  player_id: number;
  player: string;
  photo: string | null;
  team: string;
  team_logo: string | null;
  position: string | null;
  reason: string | null;
  category: "injury" | "suspension" | "other";
  status: InjuryStatus;
  since: string;
  last_missed: string;
  matches_missed: number;
  season_matches_missed: number;
  days_out: number;
  expected_return: string | null;
  expected_return_is_estimate: boolean;
  goals: number | null;
  assists: number | null;
  minutes: number | null;
  rating: number | null;
}

export interface InjuryTracker {
  as_of: string;
  season: number;
  note: string;
  current: InjuryEntry[];
  summary: {
    total: number;
    out: number;
    doubtful: number;
    suspended: number;
    by_team: { team: string; count: number; logo: string | null }[];
    top_reasons: { reason: string; count: number }[];
  };
  impact: Record<string, TeamImpact>;
}

export interface TeamAnalysis {
  team: string;
  meta: { name: string; logo: string | null; id: number | null; venue?: string; city?: string; capacity?: number; founded?: number; code?: string };
  season: number;
  position: StandingRow | null;
  overall: SplitStats;
  home: SplitStats;
  away: SplitStats;
  all_seasons: SplitStats;
  form: FormEntry[];
  form_string: string;
  streak: { type: FormResult | null; length: number };
  trend: { match: number; date: string; opponent: string; gf: number; ga: number; roll_gf: number; roll_ga: number; points: number }[];
  halves: {
    first_half_for?: number;
    second_half_for?: number;
    first_half_against?: number;
    second_half_against?: number;
    leading_at_ht?: number;
    comebacks?: number;
    points_dropped_from_winning?: number;
  };
  biggest_win: FormEntry | null;
  elo_history: { date: string; elo: number }[];
  ratings: { team: string; attack: number; defence: number } | null;
  elo: number | null;
  squad: { id: number; name: string; photo: string | null; position: string; age: number | null; appearances: number; minutes: number; goals: number; assists: number; rating: number | null }[];
  injuries: InjuryEntry[];
  availability_impact: TeamImpact;
}

export interface Fixture {
  id: number;
  kickoff: string;
  timestamp: number;
  status: string;
  status_long: string;
  elapsed: number | null;
  round: string;
  season: number;
  venue: string | null;
  home_team: string;
  home_logo: string | null;
  away_team: string;
  away_logo: string | null;
  home_score: number | null;
  away_score: number | null;
  is_live: boolean;
  prediction?: QuickPick | null;
}

export interface QuickPick {
  home_win: number;
  draw: number;
  away_win: number;
  predicted_score: string;
  pick: Outcome;
  over_2_5: number;
  btts: number;
}

export interface LiveFixtures {
  matches: Fixture[];
  today: Fixture[];
  polling: boolean;
  source: string;
  fetched_at: string | null;
}

export interface UpcomingFixtures {
  matches: Fixture[];
  source: string;
  fetched_at: string | null;
  window: string[];
  note: string;
}

export interface ResultRow {
  id: number;
  date: string;
  round: string | null;
  season: number;
  home_team: string;
  away_team: string;
  home_logo: string | null;
  away_logo: string | null;
  home_score: number;
  away_score: number;
  halftime: { home: number | null; away: number | null };
  venue: string | null;
}

export interface Results {
  live_api: { matches: Fixture[]; source: string; fetched_at: string | null };
  history: ResultRow[];
  data_as_of: string;
}

export interface SimulatedRound {
  label: string;
  matches: { home_team: string; away_team: string; home_logo: string | null; away_logo: string | null; prediction: QuickPick | null }[];
}

export interface ModelRow {
  model: string;
  accuracy: number;
  log_loss: number;
  rps: number;
  brier: number;
  n: number;
}

export interface ModelMetrics {
  status: string;
  trained_at?: string;
  training_seconds?: number;
  matches?: number;
  supervised_rows?: number;
  evaluation_rows?: number;
  seasons?: number[];
  meta_learner?: string;
  meta_candidates_rps?: Record<string, number>;
  blend_weights?: Record<string, number>;
  temperature?: number;
  half_life_days?: number;
  models?: ModelRow[];
  calibration?: { bin: string; predicted: number; observed: number; count: number }[];
  feature_importance?: { feature: string; importance: number }[];
  confidence_buckets?: { bucket: string; count: number; accuracy: number | null }[];
  outcome_distribution?: { draw: number; home: number; away: number };
  poisson?: { home_advantage: number; rho: number };
  half_life_sweep?: { half_life: number; rps: number }[];
}

export interface HistoryItem {
  id: number;
  home_team: string;
  away_team: string;
  predicted_score: string;
  predicted_outcome: Outcome | null;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  confidence: number;
  expected_goals_home: number | null;
  expected_goals_away: number | null;
  actual_score: string | null;
  created_at: string | null;
}

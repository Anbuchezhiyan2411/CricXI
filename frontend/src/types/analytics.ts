/**
 * TypeScript Interfaces for CricXI Sports Analytics & IDS Modules.
 */

export interface TossDecisionBreakdown {
  count: number;
  wins: number;
  win_rate: number;
}

export interface TossAnalysisResponse {
  total_matches: number;
  toss_winner_match_wins: number;
  observed_toss_win_rate: number;
  expected_win_rate: number;
  z_score: number;
  p_value: number;
  is_significant: boolean;
  null_hypothesis: string;
  alternative_hypothesis: string;
  conclusion: string;
  explanation: string;
  toss_decision_breakdown: {
    BAT: TossDecisionBreakdown;
    BOWL: TossDecisionBreakdown;
  };
}

export interface BattingComparisonItem {
  strategy: string;
  wins: number;
  win_rate: number;
  avg_score: number;
}

export interface BattingAnalysisResponse {
  total_matches: number;
  decisive_matches: number;
  bat_first_wins: number;
  bowl_first_wins: number;
  bat_first_win_rate: number;
  bowl_first_win_rate: number;
  avg_first_innings_score: number;
  avg_second_innings_score: number;
  best_strategy: string;
  explanation: string;
  comparison_chart: BattingComparisonItem[];
}

export interface ScatterPoint {
  match_id: number;
  team_rating: number;
  opponent_rating: number;
  rating_diff: number;
  won: boolean;
  team_name: string;
  margin: string;
}

export interface TeamRatingResponse {
  sample_size: number;
  correlation_coefficient: number;
  p_value: number;
  strength: string;
  direction: string;
  r_squared: number;
  regression_slope: number;
  regression_intercept: number;
  interpretation: string;
  scatter_points: ScatterPoint[];
}

export interface PlayerOutlierRecord {
  player_id: number;
  player_name: string;
  country: string;
  matches_played: number;
  total_runs: number;
  batting_avg: number;
  strike_rate: number;
  total_wickets: number;
  bowling_avg: number;
  economy: number;
  average_impact: number;
  z_score: number;
  category: "Elite Performer" | "Underperformer" | "Consistent Performer";
  badge: "emerald" | "rose" | "sky";
}

export interface PlayerPerformanceResponse {
  total_players: number;
  mean_impact: number;
  std_impact: number;
  elite_count: number;
  underperformer_count: number;
  players: PlayerOutlierRecord[];
}

export interface DistributionStats {
  mean: number;
  median: number;
  mode: number;
  variance: number;
  std_dev: number;
  min: number;
  max: number;
  q1: number;
  q3: number;
  iqr: number;
}

export interface HistogramBin {
  range: string;
  count: number;
  percentage: number;
}

export interface BoxplotCategory extends DistributionStats {
  category: string;
}

export interface MatchStatisticsResponse {
  total_matches: number;
  total_score: DistributionStats;
  first_innings_score: DistributionStats;
  second_innings_score: DistributionStats;
  total_wickets: DistributionStats;
  highest_score: number;
  lowest_score: number;
  average_strike_rate: number;
  average_run_rate: number;
  average_wickets: number;
  score_histogram: HistogramBin[];
  boxplot_data: BoxplotCategory[];
}

export interface CorrelationMatrixResponse {
  labels: string[];
  matrix: number[][];
  sample_size: number;
}

export interface FactorContribution {
  factor: string;
  impact: number;
}

export interface WinPredictionResponse {
  team_a_probability: number;
  team_b_probability: number;
  predicted_winner: string;
  confidence: number;
  inputs: {
    team_a_rating: number;
    team_b_rating: number;
    rating_diff: number;
    toss_winner: string;
    toss_decision: string;
    team_a_bats_first: boolean;
  };
  coefficients: {
    rating_diff_coef: number;
    toss_winner_coef: number;
    bat_first_coef: number;
    intercept: number;
  };
  factors: FactorContribution[];
  explanation: string;
  model_metadata: {
    algorithm: string;
    sample_matches_trained: number;
  };
}

export interface WinPredictionRequest {
  team_a_rating: number;
  team_b_rating: number;
  toss_winner: string;
  toss_decision: string;
}

export type AnalyticsSummary = AnalyticsSummaryResponse;
export type TeamRatingAnalysisResponse = TeamRatingResponse;

export interface AnalyticsSummaryResponse {
  total_matches: number;
  toss_analysis_summary: {
    observed_toss_win_rate: number;
    p_value: number;
    is_significant: boolean;
    conclusion: string;
  };
  batting_strategy_summary: {
    best_strategy: string;
    bat_first_win_rate: number;
    bowl_first_win_rate: number;
    avg_first_innings_score: number;
  };
  team_rating_summary: {
    correlation_coefficient: number;
    strength: string;
    direction: string;
  };
  match_highlights: {
    highest_score: number;
    lowest_score: number;
    average_strike_rate: number;
    average_run_rate: number;
    average_wickets: number;
  };
  data_science_concepts: string[];
}

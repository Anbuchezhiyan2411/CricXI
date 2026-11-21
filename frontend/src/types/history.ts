import { LiveMatchStateResponse } from "./index";

export interface InningsSummaryInfo {
  innings_number: number;
  team_name: string;
  team_user_id: string;
  total_runs: number;
  total_wickets: number;
  total_overs: number;
  run_rate: number;
  display_score: string;
}

export interface MatchHistoryItem {
  id: number;
  room_id: number;
  room_code: string;
  match_date: string | null;
  status: string;
  team1_user_id: string;
  team2_user_id: string;
  team1_name: string;
  team2_name: string;
  toss_winner_name: string | null;
  toss_decision: string | null;
  winner_user_id: string | null;
  winner_name: string | null;
  result_margin: string | null;
  innings1: InningsSummaryInfo | null;
  innings2: InningsSummaryInfo | null;
  player_of_the_match: string | null;
  player_of_the_match_details: string | null;
  has_full_scorecard: boolean;
}

export interface MatchHistoryDetail {
  match_id: number;
  room_code: string;
  match_info: MatchHistoryItem;
  scorecard: LiveMatchStateResponse | null;
}

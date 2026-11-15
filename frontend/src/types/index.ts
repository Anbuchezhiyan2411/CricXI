/**
 * TypeScript Type Definitions for CricXI.
 */

export type PlayerRole = "BAT" | "WK" | "AR" | "PACE" | "SPIN";
export type BattingHand = "Right" | "Left";
export type BowlingHand = "Right" | "Left" | "None";

export interface Player {
  id?: number;
  player_id: number;
  player_name: string;
  country: string;
  decade: number;
  batting_hand: BattingHand;
  bowling_hand: BowlingHand;
  bowling_type: string;
  primary_role: PlayerRole;
  eligible_positions: string;
  is_captain: boolean;
  is_wicketkeeper: boolean;

  // Batting Stats
  matches: number;
  innings: number;
  not_outs: number;
  runs: number;
  balls_faced: number;
  highest_score: string;
  fifties: number;
  hundreds: number;
  strike_rate: number;
  batting_average: number;
  fours: number;
  sixes: number;
  dot_balls: number;
  dot_ball_percentage: number;

  // Bowling Stats
  wickets: number;
  balls_bowled: number;
  runs_conceded: number;
  maidens: number;
  economy: number;
  bowling_average: number;
  bowling_strike_rate: number;
  four_wickets: number;
  five_wickets: number;
  dot_balls_bowled: number;
  dot_ball_percentage_bowled: number;

  // Ratings
  batting_rating: number;
  bowling_rating: number;
  fielding_rating?: number;
  overall_rating: number;
}

export type RoomStatus = "WAITING" | "DRAFTING" | "TOSS" | "LIVE" | "COMPLETED" | "ABANDONED";

export interface PlayerInRoom {
  user_id: string;
  username: string;
  is_host: boolean;
  is_ready: boolean;
  is_connected?: boolean;
  joined_at?: string;
}

export interface Room {
  room_code: string;
  host_id: string;
  status: RoomStatus;
  current_round: number;
  players: PlayerInRoom[];
  created_at?: string;
  updated_at?: string;
  is_full?: boolean;
  current_user_id?: string;
}

export interface RoomValidateResponse {
  valid: boolean;
  exists: boolean;
  is_full: boolean;
  player_count: number;
  status: string;
  message: string;
}

export interface PlayAgainResponse {
  old_room_code: string;
  new_room_code: string;
  room: Room;
  draft_state?: any;
  is_barrier_met?: boolean;
  ready_user_ids?: string[];
}

export interface DraftPick {
  id?: number;
  room_id?: number;
  round_number: number;
  user_id: string;
  player_id: number;
  player_name: string;
  batting_position: number;
  selected_country: string;
  selected_decade: number;
  primary_role?: string;
  is_captain?: boolean;
  is_wicketkeeper?: boolean;
  overall_rating?: number;
  created_at?: string;
}

export interface SquadSlot {
  slot_number: number;
  is_locked: boolean;
  pick: DraftPick | null;
}

export interface UserSquad {
  user_id: string;
  username: string;
  is_host: boolean;
  slots: SquadSlot[];
  picked_count: number;
  total_rating?: number;
}

export interface DraftStateResponse {
  room_code: string;
  current_round: number;
  total_rounds: number;
  current_turn: number;
  current_picker_id: string;
  current_picker_name: string;
  round_country: string | null;
  round_decade: number | null;
  remaining_seconds: number;
  is_finished: boolean;
  country_history: Array<[string, number]>;
  available_pool: Player[];
  candidates: Player[];
  current_pool?: Player[];
  drafted_player_ids: number[];
  host_squad: UserSquad;
  guest_squad: UserSquad;
  user_squads: Record<string, UserSquad>;
  all_picks: DraftPick[];
  updated_at?: string;
}

export interface DraftPickResponse {
  success: boolean;
  message: string;
  pick: DraftPick | null;
  is_round_complete: boolean;
  is_draft_complete: boolean;
  next_round?: number;
  next_picker_id?: string;
  next_country?: string;
  next_decade?: number;
}

export interface BallEvent {
  id: number;
  innings_id: number;
  over_number: number;
  ball_number: number;
  batsman_player_id: number;
  non_striker_player_id: number;
  bowler_player_id: number;
  runs_scored: number;
  extras: number;
  is_wicket: boolean;
  wicket_type?: string;
  dismissed_player_id?: number;
}

export interface MatchInnings {
  id: number;
  match_id: number;
  innings_number: number;
  batting_team_user_id: string;
  bowling_team_user_id: string;
  total_runs: number;
  total_wickets: number;
  total_overs: number;
  is_completed: boolean;
  ball_events?: BallEvent[];
}

export interface Match {
  id: number;
  room_id: number;
  team1_user_id: string;
  team2_user_id: string;
  toss_winner_id?: string;
  toss_decision?: "BAT" | "BOWL";
  status: string;
  winner_user_id?: string;
  result_margin?: string;
  created_at?: string;
  completed_at?: string;
  innings?: MatchInnings[];
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FilterOptions {
  countries: string[];
  decades: number[];
  roles: PlayerRole[];
}

export type TossStep = "CALLING" | "DECIDING" | "COMPLETED";
export type CoinChoice = "HEADS" | "TAILS";
export type PitchDecision = "BAT" | "BOWL";

export interface TeamInfo {
  user_id: string;
  username: string;
  is_host: boolean;
  captain_name: string;
  team_name: string;
  player_count: number;
}

export interface TossStateResponse {
  room_code: string;
  match_id?: number | null;
  step: TossStep;
  caller_id: string;
  caller_name: string;
  caller_choice?: CoinChoice | null;
  coin_result?: CoinChoice | null;
  winner_id?: string | null;
  winner_name?: string | null;
  decision?: PitchDecision | null;
  host_team: TeamInfo;
  guest_team: TeamInfo;
  is_current_user_caller: boolean;
  is_current_user_winner: boolean;
  draft_completed: boolean;
  message?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface TossCallRequest {
  user_id: string;
  choice: CoinChoice;
}

export interface TossDecisionRequest {
  user_id: string;
  decision: PitchDecision;
}

export interface BatterLiveInfo {
  player_id: number;
  player_name: string;
  batting_position: number;
  runs: number;
  balls: number;
  fours: number;
  sixes: number;
  strike_rate: number;
  is_out: boolean;
  has_batted?: boolean;
  decade?: number;
  dismissal_text: string;
  batting_status?: "OUT" | "NOT_OUT" | "DNB" | string;
}

export interface BowlerLiveInfo {
  player_id: number;
  player_name: string;
  decade?: number;
  overs: number;
  legal_balls: number;
  maidens: number;
  runs_conceded: number;
  wickets: number;
  economy: number;
  wides: number;
  no_balls: number;
}

export interface BallEventDetail {
  id?: number;
  innings_number: number;
  over_number: number;
  ball_number: number;
  legal_ball_number: number;
  batsman_player_id: number;
  batsman_name: string;
  non_striker_player_id: number;
  non_striker_name: string;
  bowler_player_id: number;
  bowler_name: string;
  batter_runs: number;
  extras: number;
  runs_scored: number;
  extra_type?: string | null;
  is_wicket: boolean;
  wicket_type?: string | null;
  dismissed_player_id?: number | null;
  dismissed_player_name?: string | null;
  commentary: string;
  description?: string | null;
  created_at?: string;
}

export interface CommentaryEntry {
  id?: number;
  innings_number: number;
  over_display: string;
  short_outcome: string;
  text: string;
  is_wicket: boolean;
  is_boundary: boolean;
  timestamp?: string;
}

export interface InningsScorecard {
  innings_number: number;
  batting_team_user_id: string;
  batting_team_name: string;
  bowling_team_user_id: string;
  bowling_team_name: string;
  total_runs: number;
  total_wickets: number;
  total_overs: number;
  legal_balls_bowled: number;
  is_completed: boolean;
  extras?: number;
  wides?: number;
  no_balls?: number;
  byes?: number;
  leg_byes?: number;
  fall_of_wickets?: string[];
  batters: BatterLiveInfo[];
  bowlers: BowlerLiveInfo[];
}

export interface TeamMatchInfo {
  user_id: string;
  username: string;
  is_host: boolean;
  captain_name: string;
  team_name: string;
}

export interface LiveMatchStateResponse {
  match_id: number;
  room_code: string;
  status: string;
  current_innings_number: number;
  host_team: TeamMatchInfo;
  guest_team: TeamMatchInfo;
  batting_team_user_id: string;
  bowling_team_user_id: string;
  batting_team_name: string;
  bowling_team_name: string;
  total_runs: number;
  total_wickets: number;
  overs: number;
  legal_balls_bowled: number;
  current_run_rate: number;
  target?: number | null;
  runs_required?: number | null;
  balls_remaining?: number | null;
  required_run_rate?: number | null;
  striker?: BatterLiveInfo | null;
  non_striker?: BatterLiveInfo | null;
  current_bowler?: BowlerLiveInfo | null;
  recent_deliveries: string[];
  last_ball?: BallEventDetail | null;
  commentary: CommentaryEntry[];
  is_paused: boolean;
  simulation_speed: number;
  winner_user_id?: string | null;
  winner_name?: string | null;
  result_margin?: string | null;
  player_of_the_match?: string | null;
  player_of_the_match_details?: string | null;
  first_innings_scorecard?: InningsScorecard | null;
  second_innings_scorecard?: InningsScorecard | null;
}

export interface SimulationControlRequest {
  action: string;
  speed?: number | null;
}




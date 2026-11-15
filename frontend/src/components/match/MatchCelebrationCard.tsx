import React from "react";
import { Trophy, Sparkles, RotateCcw, Award } from "lucide-react";
import { LiveMatchStateResponse } from "../../types";

interface MatchCelebrationCardProps {
  matchState: LiveMatchStateResponse;
  onOpenScorecard: () => void;
  onReturnToLobby: () => void;
  onPlayAgain?: () => void;
  isStartingRematch?: boolean;
  isWaitingForRematch?: boolean;
  opponentWantsRematch?: boolean;
}

export const MatchCelebrationCard: React.FC<MatchCelebrationCardProps> = ({
  matchState,
  onOpenScorecard,
  onReturnToLobby,
  onPlayAgain,
  isStartingRematch = false,
  isWaitingForRematch = false,
  opponentWantsRematch = false,
}) => {
  const {
    winner_name,
    result_margin,
    status,
    first_innings_scorecard,
    second_innings_scorecard,
    player_of_the_match,
    player_of_the_match_details,
  } = matchState;

  const isTie = status === "TIED";

  return (
    <div className="rounded-3xl cricket-card p-6 sm:p-10 shadow-2xl text-center space-y-6 relative overflow-hidden animate-in fade-in zoom-in-95 duration-500">
      {/* Glow accent */}
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#0B3D91] via-[#F4C430] to-[#138A36]" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-36 bg-[#F4C430]/15 blur-3xl pointer-events-none" />

      {/* Trophy Emblem */}
      <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-tr from-[#ca8a04] via-[#F4C430] to-[#fef08a] flex items-center justify-center text-[#081826] shadow-2xl shadow-[#F4C430]/30 border-2 border-amber-200">
        <Trophy className="w-10 h-10 stroke-[2.3] animate-bounce" />
      </div>

      <div className="space-y-2">
        <div className="inline-flex items-center space-x-1.5 px-4 py-1 rounded-full bg-[#F4C430]/15 border border-[#F4C430]/40 text-[#F4C430] text-xs font-black tracking-widest uppercase">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Match Concluded</span>
        </div>

        <h2 className="text-2xl sm:text-4xl font-black text-white uppercase tracking-tight">
          {isTie ? (
            <span className="text-[#F4C430]">Match Tied!</span>
          ) : (
            <>
              <span className="text-[#F4C430]">{winner_name}</span> Are The Champions!
            </>
          )}
        </h2>

        <p className="text-base sm:text-lg font-bold text-slate-200">
          {result_margin || "What an incredible cricket match!"}
        </p>
      </div>

      {/* Player of the Match Banner */}
      {player_of_the_match && (
        <div className="max-w-md mx-auto p-4 sm:p-5 rounded-2xl bg-[#081826] border-2 border-[#F4C430]/40 text-center shadow-xl">
          <div className="flex items-center justify-center space-x-1.5 text-[11px] font-black uppercase tracking-widest text-[#F4C430]">
            <Award className="w-4 h-4 text-[#F4C430]" />
            <span>Player of the Match</span>
          </div>
          <div className="text-xl font-black text-white mt-1">
            {player_of_the_match}
          </div>
          {player_of_the_match_details && (
            <div className="text-xs text-[#C7D2E2] font-semibold mt-1">
              {player_of_the_match_details}
            </div>
          )}
        </div>
      )}

      {/* Summary Score Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 max-w-lg mx-auto pt-2">
        {first_innings_scorecard && (
          <div className="p-4 rounded-xl bg-[#081826] border border-[#1E3A5F] text-left">
            <div className="text-[11px] font-black text-[#F4C430] uppercase tracking-wider">
              1st Innings
            </div>
            <div className="text-sm font-bold text-white truncate mt-0.5">
              {first_innings_scorecard.batting_team_name}
            </div>
            <div className="text-xl font-black text-[#F4C430] mt-1 font-mono">
              {first_innings_scorecard.total_runs}/{first_innings_scorecard.total_wickets}{" "}
              <span className="text-xs text-slate-400 font-normal">
                ({first_innings_scorecard.total_overs.toFixed(1)} ov)
              </span>
            </div>
          </div>
        )}

        {second_innings_scorecard && (
          <div className="p-4 rounded-xl bg-[#081826] border border-[#1E3A5F] text-left">
            <div className="text-[11px] font-black text-[#138A36] uppercase tracking-wider">
              2nd Innings
            </div>
            <div className="text-sm font-bold text-white truncate mt-0.5">
              {second_innings_scorecard.batting_team_name}
            </div>
            <div className="text-xl font-black text-emerald-400 mt-1 font-mono">
              {second_innings_scorecard.total_runs}/{second_innings_scorecard.total_wickets}{" "}
              <span className="text-xs text-slate-400 font-normal">
                ({second_innings_scorecard.total_overs.toFixed(1)} ov)
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Rematch Status Notice if Opponent is waiting */}
      {opponentWantsRematch && !isWaitingForRematch && (
        <div className="p-3.5 rounded-xl bg-[#F4C430]/15 border border-[#F4C430]/40 text-[#F4C430] text-xs font-black animate-pulse max-w-md mx-auto">
          ⚡ Opponent requested a rematch! Click below to start a fresh match together.
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center justify-center gap-3.5 pt-4 border-t border-[#1E3A5F]">
        <button
          onClick={onOpenScorecard}
          className="px-5 py-3 rounded-xl bg-[#081826] hover:bg-[#1E3A5F] border border-[#1E3A5F] text-white font-black text-xs uppercase tracking-wider transition-all shadow"
        >
          View Full Scorecard
        </button>

        <button
          onClick={onPlayAgain || onReturnToLobby}
          disabled={isStartingRematch || isWaitingForRematch}
          className={`inline-flex items-center space-x-2 px-7 py-3 rounded-xl text-[#081826] font-black text-xs uppercase tracking-wider transition-all shadow-xl shadow-[#F4C430]/20 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed transform hover:scale-[1.03] active:scale-[0.98] ${
            opponentWantsRematch && !isWaitingForRematch
              ? "bg-gradient-to-r from-[#F4C430] to-yellow-300 hover:from-amber-400 hover:to-yellow-200 animate-pulse"
              : "bg-gradient-to-r from-[#F4C430] to-amber-400 hover:from-amber-400 hover:to-amber-500"
          }`}
        >
          <RotateCcw className={`w-4 h-4 ${(isStartingRematch || isWaitingForRematch) ? "animate-spin" : ""}`} />
          <span>
            {isWaitingForRematch
              ? "Waiting for opponent..."
              : isStartingRematch
              ? "Starting Rematch..."
              : opponentWantsRematch
              ? "Accept & Play Rematch"
              : "Play Another Match"}
          </span>
        </button>

        <button
          onClick={onReturnToLobby}
          className="px-5 py-3 rounded-xl bg-[#081826] hover:bg-[#1E3A5F] border border-[#1E3A5F] text-[#C7D2E2] hover:text-white font-bold text-xs uppercase tracking-wider transition-all"
        >
          Return to Lobby
        </button>
      </div>
    </div>
  );
};

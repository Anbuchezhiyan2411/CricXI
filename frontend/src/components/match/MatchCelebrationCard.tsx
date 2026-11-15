import React from "react";
import { Trophy, Sparkles, RotateCcw } from "lucide-react";
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
    <div className="rounded-3xl bg-gradient-to-b from-slate-900 to-slate-950 border border-amber-500/40 p-6 sm:p-8 shadow-2xl text-center space-y-6 relative overflow-hidden animate-in fade-in zoom-in-95 duration-500">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-80 h-32 bg-amber-500/15 blur-3xl pointer-events-none" />

      {/* Trophy Emblem */}
      <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-tr from-amber-500 to-yellow-300 flex items-center justify-center text-slate-950 shadow-xl shadow-amber-500/25">
        <Trophy className="w-8 h-8 animate-bounce" />
      </div>

      <div className="space-y-2">
        <div className="inline-flex items-center space-x-1 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-black tracking-widest uppercase">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Match Concluded</span>
        </div>

        <h2 className="text-2xl sm:text-3xl font-black text-white uppercase tracking-wide">
          {isTie ? (
            <span className="text-amber-400">Match Tied!</span>
          ) : (
            <>
              <span className="text-amber-400">{winner_name}</span> Are The Champions!
            </>
          )}
        </h2>

        <p className="text-base font-bold text-slate-200">
          {result_margin || "What a thrilling match!"}
        </p>
      </div>

      {/* Player of the Match Banner */}
      {player_of_the_match && (
        <div className="max-w-md mx-auto p-4 rounded-2xl bg-gradient-to-r from-amber-500/15 via-yellow-500/20 to-amber-500/15 border border-amber-500/35 text-center shadow-lg">
          <div className="text-[10px] font-black uppercase tracking-widest text-amber-400">
            Player of the Match
          </div>
          <div className="text-lg font-black text-white mt-0.5">
            {player_of_the_match}
          </div>
          {player_of_the_match_details && (
            <div className="text-xs text-amber-200/90 font-medium mt-0.5">
              {player_of_the_match_details}
            </div>
          )}
        </div>
      )}

      {/* Summary Score Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg mx-auto pt-2">
        {first_innings_scorecard && (
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-left">
            <div className="text-[11px] font-bold text-slate-500 uppercase">
              1st Innings
            </div>
            <div className="text-sm font-bold text-white truncate">
              {first_innings_scorecard.batting_team_name}
            </div>
            <div className="text-lg font-black text-amber-300 mt-0.5">
              {first_innings_scorecard.total_runs}/{first_innings_scorecard.total_wickets}{" "}
              <span className="text-xs text-slate-400 font-normal">
                ({first_innings_scorecard.total_overs.toFixed(1)} ov)
              </span>
            </div>
          </div>
        )}

        {second_innings_scorecard && (
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-left">
            <div className="text-[11px] font-bold text-slate-500 uppercase">
              2nd Innings
            </div>
            <div className="text-sm font-bold text-white truncate">
              {second_innings_scorecard.batting_team_name}
            </div>
            <div className="text-lg font-black text-cyan-300 mt-0.5">
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
        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-bold animate-pulse max-w-md mx-auto">
          ⚡ Opponent requested a rematch! Click below to start a fresh match together.
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center justify-center gap-3 pt-4 border-t border-slate-800/80">
        <button
          onClick={onOpenScorecard}
          className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white font-bold text-xs uppercase tracking-wider transition-all"
        >
          View Full Scorecard
        </button>

        <button
          onClick={onPlayAgain || onReturnToLobby}
          disabled={isStartingRematch || isWaitingForRematch}
          className={`inline-flex items-center space-x-1.5 px-6 py-2.5 rounded-xl text-slate-950 font-black text-xs uppercase tracking-wider transition-all shadow-lg shadow-amber-500/20 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed ${
            opponentWantsRematch && !isWaitingForRematch
              ? "bg-gradient-to-r from-amber-400 to-yellow-300 hover:from-amber-300 hover:to-yellow-200 animate-pulse"
              : "bg-amber-500 hover:bg-amber-400"
          }`}
        >
          <RotateCcw className={`w-4 h-4 ${(isStartingRematch || isWaitingForRematch) ? "animate-spin" : ""}`} />
          <span>
            {isWaitingForRematch
              ? "Waiting for opponent to start another match..."
              : isStartingRematch
              ? "Starting Rematch..."
              : opponentWantsRematch
              ? "Accept & Play Another Match"
              : "Play Another Match"}
          </span>
        </button>

        <button
          onClick={onReturnToLobby}
          className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-bold text-xs uppercase tracking-wider transition-all"
        >
          Return to Lobby
        </button>
      </div>
    </div>
  );
};

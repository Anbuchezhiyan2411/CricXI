import React from "react";
import { Trophy, Activity, PauseCircle } from "lucide-react";
import { LiveMatchStateResponse } from "../../types";

interface MatchHeaderProps {
  matchState: LiveMatchStateResponse;
  onOpenScorecard: () => void;
}

export const MatchHeader: React.FC<MatchHeaderProps> = ({
  matchState,
  onOpenScorecard,
}) => {
  const {
    host_team,
    guest_team,
    room_code,
    status,
    current_innings_number,
    is_paused,
  } = matchState;

  const isCompleted = status === "COMPLETED" || status === "TIED";

  return (
    <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 border border-slate-800 p-4 sm:p-5 shadow-xl">
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Host Team Info */}
        <div className="flex items-center space-x-3 w-full md:w-auto">
          <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center font-black text-amber-400 text-base shadow-inner">
            H
          </div>
          <div>
            <div className="text-[11px] font-bold text-amber-400 uppercase tracking-wider">
              Host XI
            </div>
            <div className="text-sm sm:text-base font-black text-white leading-tight">
              {host_team.team_name}
            </div>
            <div className="text-[11px] text-slate-400">
              Capt. {host_team.captain_name}
            </div>
          </div>
        </div>

        {/* Center Match Status Badge */}
        <div className="flex flex-col items-center justify-center space-y-1.5 text-center">
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded-full bg-slate-800 border border-slate-700 font-mono text-[11px] font-bold text-slate-300">
              ROOM {room_code}
            </span>
            <div
              className={`inline-flex items-center space-x-1.5 px-3 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${
                isCompleted
                  ? "bg-emerald-500/20 border border-emerald-500/40 text-emerald-400"
                  : is_paused
                  ? "bg-amber-500/20 border border-amber-500/40 text-amber-400"
                  : "bg-red-500/20 border border-red-500/40 text-red-400 animate-pulse"
              }`}
            >
              {isCompleted ? (
                <>
                  <Trophy className="w-3.5 h-3.5" />
                  <span>Final Result</span>
                </>
              ) : is_paused ? (
                <>
                  <PauseCircle className="w-3.5 h-3.5" />
                  <span>Paused</span>
                </>
              ) : (
                <>
                  <Activity className="w-3.5 h-3.5" />
                  <span>Live • Innings {current_innings_number}</span>
                </>
              )}
            </div>
          </div>

          <div className="text-[11px] text-slate-400 font-medium">
            T20 Match • 20 Overs • 10 Wickets Max
          </div>
        </div>

        {/* Guest Team Info & Full Scorecard Action */}
        <div className="flex items-center justify-between md:justify-end space-x-3 w-full md:w-auto">
          <div className="text-right order-1 md:order-1">
            <div className="text-[11px] font-bold text-cyan-400 uppercase tracking-wider">
              Guest XI
            </div>
            <div className="text-sm sm:text-base font-black text-white leading-tight">
              {guest_team.team_name}
            </div>
            <div className="text-[11px] text-slate-400">
              Capt. {guest_team.captain_name}
            </div>
          </div>
          <div className="w-11 h-11 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center font-black text-cyan-400 text-base shadow-inner order-2 md:order-2">
            G
          </div>

          <button
            onClick={onOpenScorecard}
            className="order-3 ml-2 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-bold transition-all"
            title="View Full Scorecards"
          >
            Scorecard
          </button>
        </div>
      </div>
    </div>
  );
};

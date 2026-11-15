import React from "react";
import { Trophy, Activity, PauseCircle, FileSpreadsheet } from "lucide-react";
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
    <div className="cricket-card p-4 sm:p-5 relative overflow-hidden">
      {/* Top subtle sports gradient */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#0B3D91] via-[#F4C430] to-[#138A36]" />

      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Host Team Info */}
        <div className="flex items-center space-x-3 w-full md:w-auto">
          <div className="w-12 h-12 rounded-xl bg-[#081826] border-2 border-[#F4C430]/60 flex items-center justify-center font-black text-[#F4C430] text-lg shadow-md shadow-[#F4C430]/10">
            H
          </div>
          <div>
            <div className="text-[11px] font-black text-[#F4C430] uppercase tracking-wider">
              Host XI
            </div>
            <div className="text-sm sm:text-base font-black text-white leading-tight">
              {host_team.team_name}
            </div>
            <div className="text-[11px] text-[#C7D2E2]">
              Capt. {host_team.captain_name}
            </div>
          </div>
        </div>

        {/* Center Match Status Badge */}
        <div className="flex flex-col items-center justify-center space-y-1.5 text-center">
          <div className="flex items-center space-x-2">
            <span className="px-3 py-1 rounded-full bg-[#081826] border border-[#1E3A5F] font-mono text-xs font-bold text-[#F4C430] tracking-wider">
              ROOM {room_code}
            </span>
            <div
              className={`inline-flex items-center space-x-1.5 px-3.5 py-1 rounded-full text-xs font-black uppercase tracking-wider ${
                isCompleted
                  ? "bg-emerald-500/20 border border-emerald-500/50 text-emerald-400"
                  : is_paused
                  ? "bg-amber-500/20 border border-amber-500/50 text-amber-300"
                  : "bg-red-500/20 border border-red-500/50 text-red-400 animate-pulse"
              }`}
            >
              {isCompleted ? (
                <>
                  <Trophy className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Final Result</span>
                </>
              ) : is_paused ? (
                <>
                  <PauseCircle className="w-3.5 h-3.5 text-amber-300" />
                  <span>Paused</span>
                </>
              ) : (
                <>
                  <Activity className="w-3.5 h-3.5 text-red-400 animate-spin" />
                  <span>Live • Innings {current_innings_number}</span>
                </>
              )}
            </div>
          </div>

          <div className="text-[11px] text-[#C7D2E2] font-semibold tracking-wide">
            T20 Match • 20 Overs • 10 Wickets Max
          </div>
        </div>

        {/* Guest Team Info & Full Scorecard Action */}
        <div className="flex items-center justify-between md:justify-end space-x-3 w-full md:w-auto">
          <div className="text-right order-1 md:order-1">
            <div className="text-[11px] font-black text-[#138A36] uppercase tracking-wider">
              Guest XI
            </div>
            <div className="text-sm sm:text-base font-black text-white leading-tight">
              {guest_team.team_name}
            </div>
            <div className="text-[11px] text-[#C7D2E2]">
              Capt. {guest_team.captain_name}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-[#081826] border-2 border-[#138A36]/60 flex items-center justify-center font-black text-[#138A36] text-lg shadow-md shadow-[#138A36]/10 order-2 md:order-2">
            G
          </div>

          <button
            onClick={onOpenScorecard}
            className="order-3 ml-2 px-3.5 py-2.5 rounded-xl bg-[#081826] hover:bg-[#1E3A5F] border border-[#1E3A5F] text-[#C7D2E2] hover:text-white text-xs font-black transition-all flex items-center space-x-1.5 shadow"
            title="View Full Scorecards"
          >
            <FileSpreadsheet className="w-4 h-4 text-[#F4C430]" />
            <span>Scorecard</span>
          </button>
        </div>
      </div>
    </div>
  );
};

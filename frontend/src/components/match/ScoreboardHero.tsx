import React from "react";
import { Target, Zap, TrendingUp } from "lucide-react";
import { LiveMatchStateResponse } from "../../types";

interface ScoreboardHeroProps {
  matchState: LiveMatchStateResponse;
}

export const ScoreboardHero: React.FC<ScoreboardHeroProps> = ({ matchState }) => {
  const {
    batting_team_name,
    total_runs,
    total_wickets,
    overs,
    current_run_rate,
    current_innings_number,
    target,
    runs_required,
    balls_remaining,
    required_run_rate,
    status,
    result_margin,
  } = matchState;

  const isChase = current_innings_number === 2 && target !== null && target !== undefined;
  const isCompleted = status === "COMPLETED" || status === "TIED";

  return (
    <div className="relative overflow-hidden rounded-3xl cricket-card p-6 sm:p-8 text-center shadow-2xl">
      {/* Stadium Ambient Glow */}
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#0B3D91] via-[#F4C430] to-[#138A36]" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-32 bg-[#F4C430]/10 blur-3xl pointer-events-none" />

      {/* Batting Team Tag */}
      <div className="inline-flex items-center space-x-1.5 px-4 py-1.5 rounded-full bg-[#081826] border border-[#1E3A5F] text-[#F4C430] text-xs font-black tracking-widest uppercase mb-2 shadow-sm">
        <Zap className="w-3.5 h-3.5 text-[#F4C430]" />
        <span>{batting_team_name} Batting</span>
      </div>

      {/* Hero Scoreboard Figures */}
      <div className="my-3 flex flex-col items-center justify-center">
        <div className="flex items-baseline space-x-3 select-none">
          <span className="text-6xl sm:text-8xl font-black text-white tracking-tight drop-shadow-lg font-mono">
            {total_runs}
          </span>
          <span className="text-5xl sm:text-6xl font-light text-slate-500">/</span>
          <span className="text-5xl sm:text-7xl font-black text-[#F4C430] drop-shadow-lg font-mono">
            {total_wickets}
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-2 text-xs sm:text-sm font-bold text-[#C7D2E2] mt-2">
          <span className="px-3 py-1 rounded-lg bg-[#081826] border border-[#1E3A5F]">
            Overs: <strong className="text-white font-mono">{overs.toFixed(1)}</strong> / 20.0
          </span>
          <span className="px-3 py-1 rounded-lg bg-[#081826] border border-[#1E3A5F]">
            CRR: <strong className="text-emerald-400 font-mono">{current_run_rate.toFixed(2)}</strong>
          </span>
          <span className="px-3 py-1 rounded-lg bg-[#081826] border border-[#1E3A5F]">
            Max: <strong className="text-white">120 Balls</strong>
          </span>
        </div>
      </div>

      {/* Second Innings Chase Situation Card */}
      {isChase && !isCompleted && (
        <div className="mt-4 p-4 rounded-2xl bg-[#081826] border-2 border-[#F4C430]/40 max-w-xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs sm:text-sm shadow-xl">
          <div className="flex items-center space-x-2 text-[#F4C430] font-black">
            <Target className="w-4 h-4 text-[#F4C430]" />
            <span>
              Target: <strong className="text-white text-base font-mono">{target}</strong>
            </span>
          </div>

          <div className="text-[#C7D2E2] font-semibold text-center">
            Need{" "}
            <strong className="text-[#F4C430] font-black text-base font-mono">
              {runs_required}
            </strong>{" "}
            runs from{" "}
            <strong className="text-white font-black text-base font-mono">
              {balls_remaining}
            </strong>{" "}
            balls
          </div>

          <div className="flex items-center space-x-1.5 text-[#C7D2E2]">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            <span>
              RRR:{" "}
              <strong className="text-cyan-300 font-black font-mono">
                {required_run_rate?.toFixed(2) || "0.00"}
              </strong>
            </span>
          </div>
        </div>
      )}

      {/* Completed Banner if Finished */}
      {isCompleted && (
        <div className="mt-4 p-4 rounded-2xl bg-emerald-500/15 border-2 border-emerald-500/40 max-w-xl mx-auto text-center space-y-1 shadow-lg">
          <div className="text-base sm:text-lg font-black text-emerald-300 uppercase tracking-wide">
            {result_margin || "Match Completed!"}
          </div>
        </div>
      )}
    </div>
  );
};

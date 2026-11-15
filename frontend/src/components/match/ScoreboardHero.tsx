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
    <div className="relative overflow-hidden rounded-3xl bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border border-slate-800 p-6 sm:p-8 shadow-2xl text-center">
      {/* Ambient Top Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-28 bg-amber-500/10 blur-3xl pointer-events-none" />

      {/* Batting Team Tag */}
      <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-slate-800/90 border border-slate-700/80 text-amber-400 text-xs font-black tracking-widest uppercase mb-2">
        <Zap className="w-3.5 h-3.5" />
        <span>{batting_team_name} Batting</span>
      </div>

      {/* Hero Scoreboard Figures */}
      <div className="my-3 flex flex-col items-center justify-center">
        <div className="flex items-baseline space-x-3">
          <span className="text-5xl sm:text-7xl font-black text-white tracking-tight drop-shadow-md">
            {total_runs}
          </span>
          <span className="text-4xl sm:text-5xl font-light text-slate-500">/</span>
          <span className="text-4xl sm:text-6xl font-black text-amber-400 drop-shadow-md">
            {total_wickets}
          </span>
        </div>

        <div className="text-sm sm:text-base font-bold text-slate-400 mt-1">
          Overs:{" "}
          <span className="text-white font-black">
            {overs.toFixed(1)}
          </span>{" "}
          / 20.0
          <span className="text-slate-600 mx-2">•</span>
          <span className="text-slate-400">
            CRR:{" "}
            <span className="text-emerald-400 font-black">
              {current_run_rate.toFixed(2)}
            </span>
          </span>
        </div>
      </div>

      {/* Second Innings Chase Situation Card */}
      {isChase && !isCompleted && (
        <div className="mt-4 p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/25 max-w-lg mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs sm:text-sm">
          <div className="flex items-center space-x-2 text-amber-300 font-bold">
            <Target className="w-4 h-4 text-amber-400" />
            <span>
              Target: <strong className="text-white text-base">{target}</strong>
            </span>
          </div>

          <div className="text-slate-300 font-semibold">
            Need{" "}
            <strong className="text-amber-400 font-black text-sm">
              {runs_required}
            </strong>{" "}
            runs from{" "}
            <strong className="text-white font-bold">
              {balls_remaining}
            </strong>{" "}
            balls
          </div>

          <div className="flex items-center space-x-1.5 text-slate-400">
            <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
            <span>
              RRR:{" "}
              <strong className="text-cyan-300 font-black">
                {required_run_rate?.toFixed(2) || "0.00"}
              </strong>
            </span>
          </div>
        </div>
      )}

      {/* Completed Banner if Finished */}
      {isCompleted && (
        <div className="mt-4 p-3.5 rounded-2xl bg-emerald-500/15 border border-emerald-500/35 max-w-lg mx-auto text-center space-y-1">
          <div className="text-sm sm:text-base font-black text-emerald-400 uppercase tracking-wide">
            {result_margin || "Match Completed!"}
          </div>
        </div>
      )}
    </div>
  );
};

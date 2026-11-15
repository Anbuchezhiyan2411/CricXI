import React from "react";
import { Clock, Globe, Shield, Trophy } from "lucide-react";
import { cn } from "../../utils/helpers";

interface DraftHeaderProps {
  currentRound: number;
  totalRounds: number;
  roundCountry?: string | null;
  roundDecade?: number | null;
  remainingSeconds: number;
  isMyTurn: boolean;
  currentPickerName: string;
  countryHistory: Array<[string, number]>;
}

export const DraftHeader: React.FC<DraftHeaderProps> = ({
  currentRound,
  totalRounds,
  roundCountry,
  roundDecade,
  remainingSeconds,
  isMyTurn,
  currentPickerName,
  countryHistory,
}) => {
  // Timer styling based on remaining seconds
  const isUrgent = remainingSeconds <= 5;
  const isWarning = remainingSeconds <= 10 && remainingSeconds > 5;

  const timerColor = isUrgent
    ? "text-red-400 bg-red-500/10 border-red-500/30 animate-pulse"
    : isWarning
    ? "text-amber-400 bg-amber-500/10 border-amber-500/30"
    : "text-emerald-400 bg-emerald-500/10 border-emerald-500/30";

  return (
    <div className="w-full space-y-4">
      {/* Top Banner Card */}
      <div className="bg-surface/80 backdrop-blur-md border border-slate-800 rounded-2xl p-4 sm:p-6 shadow-xl relative overflow-hidden">
        {/* Glow ambient background based on turn */}
        <div
          className={cn(
            "absolute -top-24 -right-24 w-72 h-72 rounded-full blur-3xl pointer-events-none transition-all duration-700",
            isMyTurn ? "bg-accent/15" : "bg-purple-600/10"
          )}
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
          {/* Round & Combination Info */}
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-slate-800 border border-slate-700 text-slate-300">
                Round {currentRound} of {totalRounds}
              </span>
              <span className="text-xs text-slate-400">• T20 Draft</span>
            </div>

            <div className="flex items-center space-x-2 pt-1">
              <Globe className="w-5 h-5 text-accent shrink-0" />
              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                {roundCountry || "Selecting..."}{" "}
                <span className="text-accent">{roundDecade ? `${roundDecade}s` : ""}</span>
              </h2>
            </div>
            <p className="text-xs text-slate-400">
              Only players from this Country & Decade combination can be drafted this round.
            </p>
          </div>

          {/* Turn Announcement */}
          <div className="flex flex-col items-center justify-center text-center px-2 py-1">
            <div
              className={cn(
                "px-4 py-2 rounded-xl border text-sm font-bold flex items-center space-x-2 transition-all duration-300 shadow-md",
                isMyTurn
                  ? "bg-accent/20 border-accent text-accent animate-pulse"
                  : "bg-slate-800/80 border-slate-700 text-slate-300"
              )}
            >
              <Shield className="w-4 h-4 shrink-0" />
              <span>
                {isMyTurn ? "YOUR TURN TO PICK" : `${currentPickerName}'s Turn`}
              </span>
            </div>
            <span className="text-[11px] text-slate-400 mt-1">
              {isMyTurn
                ? "Select a player & assign batting position"
                : "Waiting for opponent selection..."}
            </span>
          </div>

          {/* Countdown Timer */}
          <div className="flex flex-col items-center md:items-end justify-center">
            <div
              className={cn(
                "flex items-center space-x-3 px-5 py-2.5 rounded-2xl border transition-all duration-300",
                timerColor
              )}
            >
              <Clock className={cn("w-6 h-6", isUrgent && "animate-spin")} />
              <div className="flex flex-col items-start leading-none">
                <span className="text-2xl sm:text-3xl font-black font-mono tracking-tight">
                  {remainingSeconds}s
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider opacity-80">
                  {isUrgent ? "Auto-Pick Soon" : "Remaining"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Combinations History Drawer / Pills */}
        {countryHistory.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-none">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider shrink-0 flex items-center space-x-1">
              <Trophy className="w-3.5 h-3.5 text-highlight" />
              <span>History:</span>
            </span>
            <div className="flex items-center space-x-1.5 flex-nowrap">
              {countryHistory.map(([c, d], idx) => (
                <span
                  key={`${c}-${d}-${idx}`}
                  className="shrink-0 px-2 py-0.5 rounded-md bg-slate-800/90 border border-slate-700 text-[11px] text-slate-300 font-medium"
                >
                  R{idx + 1}: {c} {d}s
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};


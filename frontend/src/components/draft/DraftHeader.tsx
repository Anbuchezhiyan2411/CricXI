import React from "react";
import { Globe, Shield, Trophy } from "lucide-react";
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
    ? "text-[#E53935] stroke-[#E53935]"
    : isWarning
    ? "text-[#F4C430] stroke-[#F4C430]"
    : "text-[#138A36] stroke-[#138A36]";

  // SVG circular circumference for r=26 is 2 * PI * 26 ≈ 163.36
  const circumference = 163.36;
  const strokeDashoffset = circumference - (Math.max(0, Math.min(30, remainingSeconds)) / 30) * circumference;

  return (
    <div className="w-full space-y-4">
      {/* Top Banner Card */}
      <div className="bg-[#12263A] border border-[#1E3A5F] rounded-[20px] p-5 sm:p-6 shadow-xl shadow-black/40 relative overflow-hidden backdrop-blur-xl">
        {/* Glow ambient background based on turn */}
        <div
          className={cn(
            "absolute -top-24 -right-24 w-80 h-80 rounded-full blur-3xl pointer-events-none transition-all duration-700",
            isMyTurn ? "bg-[#138A36]/15" : "bg-[#0B3D91]/25"
          )}
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
          {/* Round & Combination Info */}
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-[#081826] border border-[#1E3A5F] text-[#F4C430]">
                Round {currentRound} of {totalRounds}
              </span>
              <span className="text-xs text-[#C7D2E2] font-semibold">• Fantasy Draft</span>
            </div>

            <div className="flex items-center space-x-2.5 pt-0.5">
              <Globe className="w-5 h-5 text-[#F4C430] shrink-0" />
              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight font-display">
                {roundCountry || "Selecting..."}{" "}
                <span className="text-[#F4C430]">{roundDecade ? `${roundDecade}s` : ""}</span>
              </h2>
            </div>
            <p className="text-xs text-[#C7D2E2] font-medium leading-relaxed">
              Draft eligible cricketers exclusively from this country & decade combination.
            </p>
          </div>

          {/* Turn Announcement */}
          <div className="flex flex-col items-center justify-center text-center px-2 py-1">
            <div
              className={cn(
                "px-5 py-2.5 rounded-[14px] border text-xs sm:text-sm font-black uppercase tracking-wider flex items-center space-x-2.5 transition-all duration-300 shadow-md",
                isMyTurn
                  ? "bg-[#138A36]/20 border-[#138A36] text-[#138A36] shadow-[#138A36]/20 animate-pulse"
                  : "bg-[#081826] border-[#1E3A5F] text-[#C7D2E2]"
              )}
            >
              <Shield className={cn("w-4 h-4 shrink-0", isMyTurn ? "text-[#138A36]" : "text-[#C7D2E2]")} />
              <span>
                {isMyTurn ? "YOUR TURN TO PICK" : `${currentPickerName}'s Turn`}
              </span>
            </div>
            <span className="text-[11px] text-[#C7D2E2] font-semibold mt-1.5">
              {isMyTurn
                ? "Select a player & assign batting position"
                : "Waiting for opponent selection..."}
            </span>
          </div>

          {/* Animated Circular Countdown Timer */}
          <div className="flex items-center justify-center md:justify-end space-x-3.5">
            <div className="relative w-16 h-16 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 60 60">
                {/* Background Track */}
                <circle
                  cx="30"
                  cy="30"
                  r="26"
                  className="stroke-[#081826]"
                  strokeWidth="4"
                  fill="transparent"
                />
                {/* Progress Arc */}
                <circle
                  cx="30"
                  cy="30"
                  r="26"
                  className={cn(timerColor, "transition-all duration-1000 ease-linear")}
                  strokeWidth="4"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute flex flex-col items-center justify-center leading-none">
                <span className={cn("font-display font-black text-lg", isUrgent ? "text-[#E53935]" : isWarning ? "text-[#F4C430]" : "text-white")}>
                  {remainingSeconds}
                </span>
                <span className="text-[8px] uppercase font-black text-[#C7D2E2]">SEC</span>
              </div>
            </div>

            <div className="flex flex-col text-left">
              <span className="text-xs font-black uppercase tracking-wider text-white">
                Shot Clock
              </span>
              <span className="text-[10px] text-[#C7D2E2] font-semibold">
                {isUrgent ? "Auto-picking soon" : "30s per selection"}
              </span>
            </div>
          </div>
        </div>

        {/* Draft Round Segmented Progress Bar */}
        <div className="mt-4 pt-3 border-t border-[#1E3A5F]/60">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-black uppercase tracking-widest text-[#C7D2E2]">
              Draft Progress: Round {currentRound}/11
            </span>
            <span className="text-[10px] font-bold text-[#F4C430]">
              {Math.round((currentRound / totalRounds) * 100)}% Complete
            </span>
          </div>
          <div className="grid grid-cols-11 gap-1">
            {Array.from({ length: 11 }).map((_, rIdx) => {
              const rNum = rIdx + 1;
              const isPast = rNum < currentRound;
              const isCurrent = rNum === currentRound;
              return (
                <div
                  key={rNum}
                  className={cn(
                    "h-1.5 rounded-full transition-all",
                    isPast
                      ? "bg-[#138A36]"
                      : isCurrent
                      ? "bg-[#F4C430] animate-pulse"
                      : "bg-[#081826]"
                  )}
                  title={`Round ${rNum}`}
                />
              );
            })}
          </div>
        </div>

        {/* Combinations History Drawer / Pills */}
        {countryHistory.length > 0 && (
          <div className="mt-3 flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-none">
            <span className="text-[10px] font-black text-[#C7D2E2] uppercase tracking-wider shrink-0 flex items-center space-x-1">
              <Trophy className="w-3 h-3 text-[#F4C430]" />
              <span>Pool History:</span>
            </span>
            <div className="flex items-center space-x-1.5 flex-nowrap">
              {countryHistory.map(([c, d], idx) => (
                <span
                  key={`${c}-${d}-${idx}`}
                  className="shrink-0 px-2.5 py-0.5 rounded-full bg-[#081826] border border-[#1E3A5F] text-[10px] text-[#C7D2E2] font-bold"
                >
                  R{idx + 1}: {c} ({d}s)
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};


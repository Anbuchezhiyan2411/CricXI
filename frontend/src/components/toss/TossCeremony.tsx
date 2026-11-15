import React, { useEffect, useState } from "react";
import { Trophy, Swords, ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
import { TossStateResponse } from "../../types";

interface TossCeremonyProps {
  tossState: TossStateResponse;
  onProceedToMatch: () => void;
  countdownSeconds?: number;
}

export const TossCeremony: React.FC<TossCeremonyProps> = ({
  tossState,
  onProceedToMatch,
  countdownSeconds = 5,
}) => {
  const [secondsLeft, setSecondsLeft] = useState(countdownSeconds);
  const onProceedRef = React.useRef(onProceedToMatch);
  onProceedRef.current = onProceedToMatch;

  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          onProceedRef.current();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const { winner_name, decision, caller_name, caller_choice, coin_result, host_team, guest_team } = tossState;
  const isWinnerBatting = decision === "BAT";

  // Identify batting and bowling teams
  const winnerIsHost = tossState.winner_id === host_team.user_id;
  const battingTeam = isWinnerBatting
    ? winnerIsHost ? host_team : guest_team
    : winnerIsHost ? guest_team : host_team;
  const bowlingTeam = isWinnerBatting
    ? winnerIsHost ? guest_team : host_team
    : winnerIsHost ? host_team : guest_team;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-in fade-in zoom-in-95 duration-500">
      {/* Official Ceremony Card */}
      <div className="relative overflow-hidden rounded-2xl cricket-card p-6 sm:p-8 text-center">
        {/* Glow accent */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#0B3D91] via-[#F4C430] to-[#138A36]" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-32 bg-[#F4C430]/10 blur-3xl pointer-events-none" />

        {/* Ceremony Badge */}
        <div className="inline-flex items-center space-x-1.5 px-3.5 py-1 rounded-full bg-[#F4C430]/15 border border-[#F4C430]/40 text-[#F4C430] text-xs font-black tracking-widest uppercase mb-4">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Official Match Toss Result</span>
        </div>

        {/* Captains Meeting Header */}
        <div className="flex items-center justify-center space-x-6 my-4">
          <div className="text-right">
            <div className="text-[11px] font-black text-[#F4C430] uppercase tracking-wider">Host</div>
            <div className="text-base sm:text-lg font-black text-white">{host_team.captain_name}</div>
            <div className="text-[11px] text-[#C7D2E2]">{host_team.team_name}</div>
          </div>

          <div className="w-11 h-11 rounded-full bg-[#081826] border border-[#1E3A5F] flex items-center justify-center text-[#F4C430] shadow-md">
            <Swords className="w-5 h-5" />
          </div>

          <div className="text-left">
            <div className="text-[11px] font-black text-[#138A36] uppercase tracking-wider">Guest</div>
            <div className="text-base sm:text-lg font-black text-white">{guest_team.captain_name}</div>
            <div className="text-[11px] text-[#C7D2E2]">{guest_team.team_name}</div>
          </div>
        </div>

        {/* Toss Summary Breakdown */}
        <div className="my-6 p-4 rounded-xl bg-[#081826] border border-[#1E3A5F] max-w-lg mx-auto grid grid-cols-3 gap-2 text-center text-xs">
          <div>
            <div className="text-slate-400 font-semibold text-[11px]">Toss Caller</div>
            <div className="text-white font-bold mt-0.5 truncate">{caller_name}</div>
          </div>
          <div>
            <div className="text-slate-400 font-semibold text-[11px]">Call</div>
            <div className="text-[#F4C430] font-black mt-0.5">{caller_choice || "-"}</div>
          </div>
          <div>
            <div className="text-slate-400 font-semibold text-[11px]">Coin Result</div>
            <div className="text-emerald-400 font-black mt-0.5">{coin_result || "-"}</div>
          </div>
        </div>

        {/* Big Trophy and Decision Announcement */}
        <div className="space-y-3 py-2">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-tr from-[#ca8a04] via-[#F4C430] to-[#fef08a] text-[#081826] shadow-xl shadow-[#F4C430]/20">
            <Trophy className="w-8 h-8 stroke-[2.5]" />
          </div>

          <h2 className="text-2xl sm:text-3xl font-black text-white tracking-wide uppercase">
            <span className="text-[#F4C430]">{winner_name}</span> Won The Toss
          </h2>

          <div className="text-base sm:text-lg font-bold text-slate-200">
            and elected to{" "}
            <span className="px-3.5 py-1 rounded-lg bg-[#F4C430]/20 border border-[#F4C430]/40 text-[#F4C430] font-black uppercase tracking-wider">
              {decision === "BAT" ? "Bat First" : "Bowl First"}
            </span>
          </div>

          <p className="text-xs sm:text-sm text-[#C7D2E2] max-w-md mx-auto pt-1">
            <span className="text-white font-bold">{battingTeam.team_name}</span> will set the target in the 1st innings.{" "}
            <span className="text-white font-bold">{bowlingTeam.team_name}</span> will bowl first.
          </p>
        </div>

        {/* Progress Bar & CTA */}
        <div className="mt-8 pt-6 border-t border-[#1E3A5F] space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400 max-w-md mx-auto">
            <span className="flex items-center space-x-1.5 font-semibold text-[#138A36]">
              <ShieldCheck className="w-4 h-4 text-[#138A36]" />
              <span>Match Lineups Verified</span>
            </span>
            <span className="font-bold text-[#F4C430]">
              Entering stadium in {secondsLeft}s...
            </span>
          </div>

          {/* Animated Countdown Bar */}
          <div className="w-full max-w-md mx-auto h-2 rounded-full bg-[#081826] overflow-hidden border border-[#1E3A5F]">
            <div
              className="h-full bg-gradient-to-r from-[#F4C430] to-[#138A36] transition-all ease-linear"
              style={{
                width: `${(secondsLeft / countdownSeconds) * 100}%`,
                transitionDuration: "1000ms",
              }}
            />
          </div>

          <button
            onClick={onProceedToMatch}
            className="inline-flex items-center space-x-2 px-7 py-3.5 rounded-xl bg-gradient-to-r from-[#F4C430] via-amber-400 to-[#eab308] text-[#081826] font-black text-sm tracking-wider uppercase shadow-xl shadow-[#F4C430]/20 transition-all transform hover:scale-[1.03] active:scale-[0.98]"
          >
            <span>Enter Match Simulation Now</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

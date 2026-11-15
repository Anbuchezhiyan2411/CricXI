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
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-amber-500/30 p-6 sm:p-8 shadow-2xl text-center">
        {/* Background Ambient Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-32 bg-amber-500/10 blur-3xl pointer-events-none" />

        {/* Ceremony Badge */}
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-black tracking-widest uppercase mb-4">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Official Match Toss Result</span>
        </div>

        {/* Captains Meeting Header */}
        <div className="flex items-center justify-center space-x-6 my-4">
          <div className="text-right">
            <div className="text-xs font-bold text-amber-400 uppercase tracking-wider">Host</div>
            <div className="text-base sm:text-lg font-black text-white">{host_team.captain_name}</div>
            <div className="text-[11px] text-slate-400">{host_team.team_name}</div>
          </div>

          <div className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400">
            <Swords className="w-5 h-5 text-amber-400" />
          </div>

          <div className="text-left">
            <div className="text-xs font-bold text-cyan-400 uppercase tracking-wider">Guest</div>
            <div className="text-base sm:text-lg font-black text-white">{guest_team.captain_name}</div>
            <div className="text-[11px] text-slate-400">{guest_team.team_name}</div>
          </div>
        </div>

        {/* Toss Summary Breakdown */}
        <div className="my-6 p-4 rounded-xl bg-slate-950/70 border border-slate-800 max-w-lg mx-auto grid grid-cols-3 gap-2 text-center text-xs">
          <div>
            <div className="text-slate-500 font-medium">Toss Caller</div>
            <div className="text-slate-200 font-bold mt-0.5 truncate">{caller_name}</div>
          </div>
          <div>
            <div className="text-slate-500 font-medium">Call</div>
            <div className="text-amber-400 font-black mt-0.5">{caller_choice || "-"}</div>
          </div>
          <div>
            <div className="text-slate-500 font-medium">Coin Result</div>
            <div className="text-amber-300 font-black mt-0.5">{coin_result || "-"}</div>
          </div>
        </div>

        {/* Big Trophy and Decision Announcement */}
        <div className="space-y-3 py-2">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-tr from-amber-600 to-yellow-400 text-slate-950 shadow-lg shadow-amber-500/20">
            <Trophy className="w-8 h-8" />
          </div>

          <h2 className="text-2xl sm:text-3xl font-black text-white tracking-wide uppercase">
            <span className="text-amber-400">{winner_name}</span> Won The Toss
          </h2>

          <div className="text-base sm:text-lg font-bold text-slate-200">
            and elected to{" "}
            <span className="px-3 py-1 rounded bg-amber-500/20 border border-amber-500/40 text-amber-300 font-black uppercase tracking-wider">
              {decision === "BAT" ? "Bat First" : "Bowl First"}
            </span>
          </div>

          <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto pt-1">
            <span className="text-white font-semibold">{battingTeam.team_name}</span> will set the target in the 1st innings.{" "}
            <span className="text-white font-semibold">{bowlingTeam.team_name}</span> will bowl first.
          </p>
        </div>

        {/* Progress Bar & CTA */}
        <div className="mt-8 pt-6 border-t border-slate-800/80 space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400 max-w-md mx-auto">
            <span className="flex items-center space-x-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Match Lineups Verified</span>
            </span>
            <span className="font-semibold text-amber-400">
              Entering stadium in {secondsLeft}s...
            </span>
          </div>

          {/* Animated Countdown Bar */}
          <div className="w-full max-w-md mx-auto h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-amber-500 to-yellow-400 transition-all ease-linear"
              style={{
                width: `${(secondsLeft / countdownSeconds) * 100}%`,
                transitionDuration: "1000ms",
              }}
            />
          </div>

          <button
            onClick={onProceedToMatch}
            className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-black text-sm tracking-wider uppercase shadow-lg shadow-amber-500/25 transition-all transform hover:scale-[1.02] active:scale-[0.98]"
          >
            <span>Enter Match Simulation Now</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};


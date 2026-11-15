import React from "react";
import { Crown, Shield, Star, Award, CheckCircle } from "lucide-react";
import { Player } from "../../types";
import { Badge } from "../common/Badge";
import { Button } from "../common/Button";
import { cn } from "../../utils/helpers";

interface CandidateCardProps {
  player: Player;
  isMyTurn: boolean;
  isDrafted: boolean;
  onSelect: (player: Player) => void;
}

export const CandidateCard: React.FC<CandidateCardProps> = ({
  player,
  isMyTurn,
  isDrafted,
  onSelect,
}) => {
  // Parse positions for clean presentation
  const positions = (player.eligible_positions || "")
    .replace(/\|/g, ", ")
    .replace(/, /g, ", ");

  // Initials for avatar
  const initials = player.player_name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div
      className={cn(
        "relative rounded-xl border p-4 transition-all duration-200 flex flex-col justify-between overflow-hidden",
        isDrafted
          ? "bg-slate-900/40 border-slate-800 opacity-40 pointer-events-none"
          : "bg-surface/90 border-slate-800 hover:border-slate-700 hover:shadow-lg hover:shadow-black/20"
      )}
    >
      {/* Drafted Overlay Indicator */}
      {isDrafted && (
        <div className="absolute top-2 right-2 flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] font-bold">
          <CheckCircle className="w-3 h-3 text-emerald-400" />
          <span>DRAFTED</span>
        </div>
      )}

      {/* Card Header: Avatar + Info */}
      <div className="space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            {/* Player Avatar Placeholder */}
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 flex items-center justify-center font-bold text-slate-300 text-sm shadow-inner shrink-0">
              {initials}
            </div>

            <div>
              <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
                <h3 className="font-extrabold text-sm sm:text-base text-white leading-tight">
                  {player.player_name}
                </h3>
                {player.is_captain && (
                  <span
                    title="Captain Eligible"
                    className="inline-flex items-center space-x-0.5 px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-extrabold"
                  >
                    <Crown className="w-2.5 h-2.5" />
                    <span>C</span>
                  </span>
                )}
                {player.is_wicketkeeper && (
                  <span
                    title="Wicketkeeper"
                    className="inline-flex items-center space-x-0.5 px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px] font-extrabold"
                  >
                    <Award className="w-2.5 h-2.5" />
                    <span>WK</span>
                  </span>
                )}
              </div>
              <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
                <Badge variant="role" roleType={player.primary_role} className="text-[10px] py-0">
                  {player.primary_role}
                </Badge>
                <span>•</span>
                <span>{player.country}</span>
              </div>
            </div>
          </div>

          {/* Overall Rating Pill */}
          <div className="flex flex-col items-end">
            <div className="flex items-center space-x-1 px-2 py-1 rounded-lg bg-accent/15 border border-accent/30 text-accent font-black text-sm">
              <Star className="w-3.5 h-3.5 fill-accent" />
              <span>{Math.round(player.overall_rating || 0)}</span>
            </div>
            <span className="text-[9px] uppercase tracking-wider text-slate-400 font-bold mt-0.5">
              OVR
            </span>
          </div>
        </div>

        {/* Player Styles */}
        <div className="text-[11px] text-slate-300 space-y-0.5 bg-slate-900/50 rounded-lg p-2 border border-slate-800/80">
          <div className="flex justify-between">
            <span className="text-slate-400">Batting:</span>
            <span className="font-medium">{player.batting_hand} hand</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Bowling:</span>
            <span className="font-medium truncate max-w-[140px]" title={player.bowling_type || player.bowling_hand}>
              {player.bowling_type && player.bowling_type !== "None"
                ? player.bowling_type
                : `${player.bowling_hand} arm`}
            </span>
          </div>
        </div>

        {/* Detailed Ratings Bar */}
        <div className="grid grid-cols-3 gap-1.5 text-center">
          <div className="rounded-lg bg-slate-900/80 border border-slate-800 p-1.5">
            <span className="text-[10px] text-slate-400 block uppercase font-semibold">BAT</span>
            <span className="text-xs font-bold text-white">
              {Math.round(player.batting_rating || 0)}
            </span>
          </div>
          <div className="rounded-lg bg-slate-900/80 border border-slate-800 p-1.5">
            <span className="text-[10px] text-slate-400 block uppercase font-semibold">BOWL</span>
            <span className="text-xs font-bold text-white">
              {Math.round(player.bowling_rating || 0)}
            </span>
          </div>
          <div className="rounded-lg bg-slate-900/80 border border-slate-800 p-1.5">
            <span className="text-[10px] text-slate-400 block uppercase font-semibold">FLD</span>
            <span className="text-xs font-bold text-white">
              {Math.round(player.fielding_rating || 75)}
            </span>
          </div>
        </div>

        {/* Position Eligibility */}
        <div className="flex items-center space-x-1.5 text-[11px] text-slate-400 px-1">
          <Shield className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="text-slate-400">Eligible:</span>
          <span className="font-semibold text-slate-200">{positions || "Any"}</span>
        </div>
      </div>

      {/* Select / Pick Button */}
      <div className="mt-4 pt-3 border-t border-slate-800/80">
        <Button
          type="button"
          variant={isMyTurn ? "primary" : "outline"}
          size="sm"
          disabled={!isMyTurn || isDrafted}
          onClick={() => onSelect(player)}
          className="w-full text-xs font-bold py-2 justify-center"
        >
          {isDrafted
            ? "Already Drafted"
            : isMyTurn
            ? "Select Player"
            : "Waiting Turn"}
        </Button>
      </div>
    </div>
  );
};

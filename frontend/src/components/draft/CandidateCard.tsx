import React from "react";
import { Crown, Shield, Award, CheckCircle } from "lucide-react";
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

  const ovr = Math.round(player.overall_rating || 0);

  return (
    <div
      className={cn(
        "relative rounded-[18px] border p-4.5 transition-all duration-300 flex flex-col justify-between overflow-hidden group select-none",
        isDrafted
          ? "bg-[#081826]/60 border-[#1E3A5F]/40 opacity-40 pointer-events-none"
          : isMyTurn
          ? "bg-[#12263A] border-[#1E3A5F] hover:border-[#F4C430]/60 hover:shadow-xl hover:shadow-[#0B3D91]/25 hover:-translate-y-1"
          : "bg-[#12263A]/90 border-[#1E3A5F]/70 hover:border-[#1E3A5F]"
      )}
    >
      {/* Drafted Overlay Indicator */}
      {isDrafted && (
        <div className="absolute top-2.5 right-2.5 z-10 flex items-center space-x-1 px-2.5 py-1 rounded-full bg-[#081826]/90 border border-[#1E3A5F] text-[#C7D2E2] text-[10px] font-black uppercase tracking-wider">
          <CheckCircle className="w-3 h-3 text-[#138A36]" />
          <span>DRAFTED</span>
        </div>
      )}

      {/* Card Header: Avatar + Info */}
      <div className="space-y-3.5">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center space-x-3">
            {/* Player Avatar Card Badge */}
            <div className="w-12 h-12 rounded-[14px] bg-gradient-to-tr from-[#0B3D91] via-[#1E3A5F] to-[#12263A] border border-[#1E3A5F] flex items-center justify-center font-display font-black text-white text-base shadow-md group-hover:scale-105 transition-transform shrink-0">
              {initials}
            </div>

            <div>
              <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
                <h3 className="font-display font-black text-sm sm:text-base text-white leading-tight group-hover:text-[#F4C430] transition-colors">
                  {player.player_name}
                </h3>
                {player.is_captain && (
                  <span
                    title="Captain Eligible"
                    className="inline-flex items-center space-x-0.5 px-1.5 py-0.5 rounded-full bg-[#F4C430]/20 text-[#F4C430] border border-[#F4C430]/40 text-[9px] font-black"
                  >
                    <Crown className="w-2.5 h-2.5" />
                    <span>C</span>
                  </span>
                )}
                {player.is_wicketkeeper && (
                  <span
                    title="Wicketkeeper"
                    className="inline-flex items-center space-x-0.5 px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/40 text-[9px] font-black"
                  >
                    <Award className="w-2.5 h-2.5" />
                    <span>WK</span>
                  </span>
                )}
              </div>
              <div className="flex items-center space-x-2 text-[11px] text-[#C7D2E2] mt-1 font-semibold">
                <Badge variant="role" roleType={player.primary_role} className="text-[10px] py-0 px-2 font-bold">
                  {player.primary_role}
                </Badge>
                <span>•</span>
                <span className="text-[#C7D2E2]">{player.country}</span>
              </div>
            </div>
          </div>

          {/* Overall Rating Circular / Shield Badge */}
          {!isDrafted && (
            <div className="flex flex-col items-center shrink-0">
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#F4C430] via-[#D4A516] to-[#F4C430] p-0.5 shadow-md shadow-[#F4C430]/25">
                <div className="w-full h-full rounded-full bg-[#081826] flex items-center justify-center">
                  <span className="font-display font-black text-sm text-[#F4C430] leading-none">
                    {ovr}
                  </span>
                </div>
              </div>
              <span className="text-[8px] uppercase tracking-widest text-[#C7D2E2] font-black mt-0.5">
                OVR
              </span>
            </div>
          )}
        </div>

        {/* Player Styles */}
        <div className="text-[11px] text-[#C7D2E2] space-y-1 bg-[#081826]/80 rounded-[12px] p-2.5 border border-[#1E3A5F]/70">
          <div className="flex justify-between items-center">
            <span className="text-[#C7D2E2]/70 font-semibold">Batting:</span>
            <span className="font-bold text-white">{player.batting_hand} hand</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#C7D2E2]/70 font-semibold">Bowling:</span>
            <span className="font-bold text-white truncate max-w-[140px]" title={player.bowling_type || player.bowling_hand}>
              {player.bowling_type && player.bowling_type !== "None"
                ? player.bowling_type
                : `${player.bowling_hand} arm`}
            </span>
          </div>
        </div>

        {/* Detailed Ratings Bar */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-[10px] bg-[#081826] border border-[#1E3A5F] p-1.5 shadow-inner">
            <span className="text-[9px] text-[#C7D2E2] block uppercase font-bold tracking-wider">BAT</span>
            <span className="text-xs font-black text-white font-display">
              {Math.round(player.batting_rating || 0)}
            </span>
          </div>
          <div className="rounded-[10px] bg-[#081826] border border-[#1E3A5F] p-1.5 shadow-inner">
            <span className="text-[9px] text-[#C7D2E2] block uppercase font-bold tracking-wider">BOWL</span>
            <span className="text-xs font-black text-white font-display">
              {Math.round(player.bowling_rating || 0)}
            </span>
          </div>
          <div className="rounded-[10px] bg-[#081826] border border-[#1E3A5F] p-1.5 shadow-inner">
            <span className="text-[9px] text-[#C7D2E2] block uppercase font-bold tracking-wider">FLD</span>
            <span className="text-xs font-black text-white font-display">
              {Math.round(player.fielding_rating || 75)}
            </span>
          </div>
        </div>

        {/* Position Eligibility */}
        <div className="flex items-center space-x-1.5 text-[11px] text-[#C7D2E2] px-0.5">
          <Shield className="w-3.5 h-3.5 text-[#138A36] shrink-0" />
          <span className="text-[#C7D2E2]/70 font-semibold">Eligible:</span>
          <span className="font-bold text-white truncate">{positions || "Any Position"}</span>
        </div>
      </div>

      {/* Select / Pick Button */}
      <div className="mt-4 pt-3 border-t border-[#1E3A5F]/70">
        <Button
          type="button"
          variant={isDrafted ? "secondary" : isMyTurn ? "gold" : "secondary"}
          size="sm"
          disabled={!isMyTurn || isDrafted}
          onClick={() => onSelect(player)}
          className={cn(
            "w-full text-xs font-black py-2.5 justify-center tracking-wider",
            isMyTurn && !isDrafted && "shadow-lg shadow-[#F4C430]/20 animate-pulse"
          )}
        >
          {isDrafted
            ? "Already Drafted"
            : isMyTurn
            ? "Draft Player"
            : "Waiting Turn"}
        </Button>
      </div>
    </div>
  );
};

import React, { useState } from "react";
import { Crown, Award, Star, Users, User, ShieldCheck } from "lucide-react";
import { UserSquad } from "../../types";
import { Badge } from "../common/Badge";
import { cn } from "../../utils/helpers";

interface BestXIPanelProps {
  mySquad: UserSquad | null;
  opponentSquad: UserSquad | null;
  myUsername: string;
  opponentUsername: string;
}

const POSITION_DESCRIPTIONS: Record<number, string> = {
  1: "Opener",
  2: "Opener",
  3: "Top Order (No. 3)",
  4: "Middle Order",
  5: "Middle Order",
  6: "All-Rounder / Finisher",
  7: "Lower Middle",
  8: "Lower Order",
  9: "Bowler",
  10: "Bowler",
  11: "Bowler / Tail",
};

export const BestXIPanel: React.FC<BestXIPanelProps> = ({
  mySquad,
  opponentSquad,
  myUsername,
  opponentUsername,
}) => {
  const [activeTab, setActiveTab] = useState<"mine" | "opponent">("mine");

  const renderSquadSlots = (squad: UserSquad | null) => {
    const slots = [];
    for (let pos = 1; pos <= 11; pos++) {
      const slotData = squad?.slots?.find((s) => s.slot_number === pos);
      const pick = slotData?.pick;

      slots.push(
        <div
          key={pos}
          className={cn(
            "p-3 rounded-[14px] border transition-all duration-200 flex items-center justify-between text-xs",
            pick
              ? "bg-[#081826]/90 border-[#1E3A5F] shadow-sm hover:border-[#F4C430]/40"
              : "bg-[#081826]/40 border-dashed border-[#1E3A5F]/60 text-[#C7D2E2]/60"
          )}
        >
          {/* Position Number & Player Info */}
          <div className="flex items-center space-x-3 min-w-0">
            <span
              className={cn(
                "w-7 h-7 rounded-lg flex items-center justify-center font-mono font-black text-xs shrink-0 shadow-inner",
                pick
                  ? "bg-[#0B3D91] text-[#F4C430] border border-[#F4C430]/30"
                  : "bg-[#12263A] text-[#C7D2E2]/60 border border-[#1E3A5F]"
              )}
            >
              {pos}
            </span>

            {pick ? (
              <div className="min-w-0">
                <div className="flex items-center space-x-1.5 flex-wrap">
                  <span className="font-display font-black text-white truncate max-w-[150px] sm:max-w-[200px]">
                    {pick.player_name}
                  </span>
                  {pick.is_captain && (
                    <span
                      title="Captain"
                      className="inline-flex items-center space-x-0.5 px-1.5 py-0.2 rounded-full bg-[#F4C430]/20 text-[#F4C430] border border-[#F4C430]/40 text-[9px] font-black"
                    >
                      <Crown className="w-2.5 h-2.5" />
                      <span>C</span>
                    </span>
                  )}
                  {pick.is_wicketkeeper && (
                    <span
                      title="Wicketkeeper"
                      className="inline-flex items-center space-x-0.5 px-1.5 py-0.2 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/40 text-[9px] font-black"
                    >
                      <Award className="w-2.5 h-2.5" />
                      <span>WK</span>
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-2 text-[10px] text-[#C7D2E2] mt-0.5 font-medium">
                  {pick.primary_role && (
                    <Badge variant="role" roleType={pick.primary_role} className="text-[9px] py-0 px-1.5 font-bold">
                      {pick.primary_role}
                    </Badge>
                  )}
                  <span>•</span>
                  <span>{pick.selected_country}</span>
                  <span>•</span>
                  <span className="text-[#F4C430]/80 font-bold">{POSITION_DESCRIPTIONS[pos]}</span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col">
                <span className="font-bold text-[#C7D2E2]/70">Open Slot {pos}</span>
                <span className="text-[10px] text-[#C7D2E2]/50 font-medium">{POSITION_DESCRIPTIONS[pos]}</span>
              </div>
            )}
          </div>

          {/* Rating or Placeholder */}
          {pick ? (
            <div className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-[#F4C430]/15 border border-[#F4C430]/30 text-[#F4C430] font-black text-xs shrink-0 font-display">
              <Star className="w-3 h-3 fill-current" />
              <span>{Math.round(pick.overall_rating || 0)}</span>
            </div>
          ) : (
            <span className="text-[10px] text-[#C7D2E2]/40 font-mono uppercase font-bold shrink-0">Vacant</span>
          )}
        </div>
      );
    }
    return slots;
  };

  const activeSquad = activeTab === "mine" ? mySquad : opponentSquad;
  const activeName = activeTab === "mine" ? myUsername : opponentUsername;
  const count = activeSquad?.picked_count || 0;
  const avgRating = activeSquad?.total_rating ? Math.round(activeSquad.total_rating) : 0;

  return (
    <div className="bg-[#12263A] border border-[#1E3A5F] rounded-[20px] p-5 shadow-xl shadow-black/30 space-y-4 backdrop-blur-xl">
      {/* Panel Header & Tabs */}
      <div className="flex items-center justify-between pb-3.5 border-b border-[#1E3A5F]/80">
        <div className="flex items-center space-x-2.5">
          <ShieldCheck className="w-5 h-5 text-[#138A36]" />
          <h3 className="font-display font-black text-base text-white truncate max-w-[140px] sm:max-w-[180px]">
            {activeName}'s XI
          </h3>
        </div>

        {/* Tab switch */}
        <div className="flex items-center space-x-1 p-1 bg-[#081826] border border-[#1E3A5F] rounded-xl">
          <button
            type="button"
            onClick={() => setActiveTab("mine")}
            className={cn(
              "px-3.5 py-1 rounded-lg text-xs font-black uppercase tracking-wider transition-all flex items-center space-x-1.5",
              activeTab === "mine"
                ? "bg-[#0B3D91] text-[#F4C430] shadow-sm border border-[#F4C430]/30"
                : "text-[#C7D2E2] hover:text-white"
            )}
          >
            <User className="w-3.5 h-3.5" />
            <span>My XI</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("opponent")}
            className={cn(
              "px-3.5 py-1 rounded-lg text-xs font-black uppercase tracking-wider transition-all flex items-center space-x-1.5",
              activeTab === "opponent"
                ? "bg-[#0B3D91] text-[#F4C430] shadow-sm border border-[#F4C430]/30"
                : "text-[#C7D2E2] hover:text-white"
            )}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Opponent</span>
          </button>
        </div>
      </div>

      {/* Squad Summary Stats Bar */}
      <div className="grid grid-cols-2 gap-3 bg-[#081826] p-3 rounded-[14px] border border-[#1E3A5F] text-center">
        <div>
          <span className="text-[10px] text-[#C7D2E2] uppercase font-black tracking-wider block">
            Drafted Slots
          </span>
          <span className="text-base font-black text-white font-display">
            {count} <span className="text-xs text-[#C7D2E2] font-semibold">/ 11</span>
          </span>
        </div>
        <div>
          <span className="text-[10px] text-[#C7D2E2] uppercase font-black tracking-wider block">
            Squad Avg OVR
          </span>
          <span className="text-base font-black text-[#F4C430] font-display">
            {avgRating > 0 ? avgRating : "—"}
          </span>
        </div>
      </div>

      {/* 11 Slots List */}
      <div className="space-y-2 max-h-[620px] overflow-y-auto pr-1">
        {renderSquadSlots(activeSquad)}
      </div>
    </div>
  );
};

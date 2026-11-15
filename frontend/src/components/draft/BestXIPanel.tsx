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
            "p-2.5 rounded-xl border transition-all duration-200 flex items-center justify-between text-xs",
            pick
              ? "bg-surface/90 border-slate-700/80 shadow-sm"
              : "bg-slate-900/40 border-dashed border-slate-800 text-slate-400"
          )}
        >
          {/* Position Number & Player Info */}
          <div className="flex items-center space-x-3 min-w-0">
            <span
              className={cn(
                "w-6 h-6 rounded-lg flex items-center justify-center font-mono font-bold text-xs shrink-0",
                pick
                  ? "bg-accent/20 text-accent border border-accent/30"
                  : "bg-slate-800 text-slate-400"
              )}
            >
              {pos}
            </span>

            {pick ? (
              <div className="min-w-0">
                <div className="flex items-center space-x-1.5 flex-wrap">
                  <span className="font-extrabold text-white truncate max-w-[150px] sm:max-w-[200px]">
                    {pick.player_name}
                  </span>
                  {pick.is_captain && (
                    <span
                      title="Captain"
                      className="inline-flex items-center space-x-0.5 px-1 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[9px] font-black"
                    >
                      <Crown className="w-2.5 h-2.5" />
                      <span>C</span>
                    </span>
                  )}
                  {pick.is_wicketkeeper && (
                    <span
                      title="Wicketkeeper"
                      className="inline-flex items-center space-x-0.5 px-1 py-0.2 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[9px] font-black"
                    >
                      <Award className="w-2.5 h-2.5" />
                      <span>WK</span>
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-2 text-[10px] text-slate-400">
                  {pick.primary_role && (
                    <Badge variant="role" roleType={pick.primary_role} className="text-[9px] py-0 px-1.5">
                      {pick.primary_role}
                    </Badge>
                  )}
                  <span>•</span>
                  <span>{pick.selected_country}</span>
                  <span>•</span>
                  <span className="text-slate-400">{POSITION_DESCRIPTIONS[pos]}</span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col">
                <span className="font-semibold text-slate-400">Open Slot</span>
                <span className="text-[10px] text-slate-400">{POSITION_DESCRIPTIONS[pos]}</span>
              </div>
            )}
          </div>

          {/* Rating or Placeholder */}
          {pick ? (
            <div className="flex items-center space-x-1 px-2 py-1 rounded-md bg-accent/15 border border-accent/25 text-accent font-bold text-xs shrink-0">
              <Star className="w-3 h-3 fill-accent" />
              <span>{Math.round(pick.overall_rating || 0)}</span>
            </div>
          ) : (
            <span className="text-[10px] text-slate-400 font-mono italic shrink-0">Empty</span>
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
    <div className="bg-surface/80 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-xl space-y-4">
      {/* Panel Header & Tabs */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-accent" />
          <h3 className="font-extrabold text-base text-white truncate max-w-[140px] sm:max-w-[180px]">
            {activeName}'s XI
          </h3>
        </div>

        {/* Tab switch */}
        <div className="flex items-center space-x-1 p-1 bg-slate-900 border border-slate-800 rounded-xl">
          <button
            type="button"
            onClick={() => setActiveTab("mine")}
            className={cn(
              "px-3 py-1 rounded-lg text-xs font-bold transition-all flex items-center space-x-1",
              activeTab === "mine"
                ? "bg-accent text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <User className="w-3.5 h-3.5" />
            <span>My XI</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("opponent")}
            className={cn(
              "px-3 py-1 rounded-lg text-xs font-bold transition-all flex items-center space-x-1",
              activeTab === "opponent"
                ? "bg-accent text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Opponent</span>
          </button>
        </div>
      </div>

      {/* Squad Summary Stats Bar */}
      <div className="grid grid-cols-2 gap-2 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80 text-center">
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-bold block">
            Drafted Slots
          </span>
          <span className="text-sm font-extrabold text-white">
            {count} / 11
          </span>
        </div>
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-bold block">
            Squad Avg OVR
          </span>
          <span className="text-sm font-extrabold text-accent">
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

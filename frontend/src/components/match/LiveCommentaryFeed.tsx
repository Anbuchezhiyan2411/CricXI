import React from "react";
import { MessageSquareText } from "lucide-react";
import { CommentaryEntry } from "../../types";

interface LiveCommentaryFeedProps {
  commentary: CommentaryEntry[];
}

export const LiveCommentaryFeed: React.FC<LiveCommentaryFeedProps> = ({
  commentary,
}) => {
  const getOutcomeBadge = (tok: string, isWicket: boolean, isBoundary: boolean) => {
    if (isWicket) {
      return "bg-gradient-to-tr from-red-700 to-[#E53935] text-white border-red-400 font-black shadow-sm";
    }
    if (isBoundary) {
      return tok === "6"
        ? "bg-purple-700 text-[#F4C430] border-purple-400 font-black shadow-sm"
        : "bg-[#F4C430] text-[#081826] border-amber-300 font-black shadow-sm";
    }
    if (tok.includes("Wd") || tok.includes("Nb")) {
      return "bg-amber-500/20 text-amber-300 border-amber-500/50 font-bold";
    }
    return "bg-[#081826] text-[#C7D2E2] border-[#1E3A5F] font-bold";
  };

  return (
    <div className="cricket-card p-4 sm:p-5 shadow-lg space-y-3">
      <div className="flex items-center space-x-2 border-b border-[#1E3A5F] pb-2.5">
        <MessageSquareText className="w-4 h-4 text-[#F4C430]" />
        <h4 className="text-xs font-black uppercase tracking-wider text-[#C7D2E2]">
          Ball-by-Ball Live Commentary
        </h4>
      </div>

      <div className="max-h-80 overflow-y-auto space-y-2.5 pr-1 divide-y divide-[#1E3A5F]/40 scrollbar-thin">
        {commentary.length > 0 ? (
          commentary.map((entry, idx) => (
            <div
              key={entry.id || idx}
              className={`pt-2.5 flex items-start space-x-3 text-xs leading-relaxed transition-all ${
                entry.is_wicket
                  ? "bg-red-500/10 -mx-2 px-2.5 py-2 rounded-xl border-l-4 border-[#E53935]"
                  : entry.is_boundary
                  ? "bg-[#F4C430]/10 -mx-2 px-2.5 py-2 rounded-xl border-l-4 border-[#F4C430]"
                  : ""
              }`}
            >
              {/* Over Number */}
              <div className="font-mono font-bold text-slate-400 w-10 shrink-0 pt-0.5 text-[11px]">
                {entry.over_display}
              </div>

              {/* Short Outcome Badge */}
              <div
                className={`w-6 h-6 shrink-0 rounded-full border flex items-center justify-center text-[10px] font-mono ${getOutcomeBadge(
                  entry.short_outcome,
                  entry.is_wicket,
                  entry.is_boundary
                )}`}
              >
                {entry.short_outcome}
              </div>

              {/* Commentary Prose */}
              <div className="text-slate-200 font-normal grow">
                {entry.text}
              </div>
            </div>
          ))
        ) : (
          <div className="py-8 text-center text-slate-400 italic text-xs">
            Simulation starting... awaiting first delivery commentary.
          </div>
        )}
      </div>
    </div>
  );
};

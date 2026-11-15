import React, { useState, useMemo } from "react";
import { Search, Filter, ArrowUpDown, Users } from "lucide-react";
import { Player, PlayerRole } from "../../types";
import { CandidateCard } from "./CandidateCard";
import { cn } from "../../utils/helpers";

interface CandidatePoolProps {
  candidates: Player[];
  draftedIds: number[];
  isMyTurn: boolean;
  onSelectPlayer: (player: Player) => void;
}

type SortOption = "overall" | "batting" | "bowling" | "name";

const ROLE_TABS: Array<{ label: string; role: PlayerRole | "ALL" }> = [
  { label: "All", role: "ALL" },
  { label: "BAT", role: "BAT" },
  { label: "WK", role: "WK" },
  { label: "AR", role: "AR" },
  { label: "PACE", role: "PACE" },
  { label: "SPIN", role: "SPIN" },
];

export const CandidatePool: React.FC<CandidatePoolProps> = ({
  candidates,
  draftedIds,
  isMyTurn,
  onSelectPlayer,
}) => {
  const [search, setSearch] = useState("");
  const [selectedRole, setSelectedRole] = useState<PlayerRole | "ALL">("ALL");
  const [sortBy, setSortBy] = useState<SortOption>("overall");

  const filteredAndSortedPlayers = useMemo(() => {
    return candidates
      .filter((player) => {
        // Name search
        if (
          search.trim() &&
          !player.player_name.toLowerCase().includes(search.toLowerCase().trim())
        ) {
          return false;
        }
        // Role filter
        if (selectedRole !== "ALL" && player.primary_role !== selectedRole) {
          return false;
        }
        return true;
      })
      .sort((a, b) => {
        // First prioritize undrafted over drafted
        const aDrafted = draftedIds.includes(a.player_id);
        const bDrafted = draftedIds.includes(b.player_id);
        if (aDrafted !== bDrafted) return aDrafted ? 1 : -1;

        if (sortBy === "overall") return (b.overall_rating || 0) - (a.overall_rating || 0);
        if (sortBy === "batting") return (b.batting_rating || 0) - (a.batting_rating || 0);
        if (sortBy === "bowling") return (b.bowling_rating || 0) - (a.bowling_rating || 0);
        if (sortBy === "name") return a.player_name.localeCompare(b.player_name);
        return 0;
      });
  }, [candidates, draftedIds, search, selectedRole, sortBy]);

  const availableCount = candidates.filter((p) => !draftedIds.includes(p.player_id)).length;

  return (
    <div className="space-y-4">
      {/* Search, Filter & Sort Controls */}
      <div className="bg-surface/80 border border-slate-800 rounded-2xl p-4 space-y-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search player name..."
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-700/80 text-xs sm:text-sm text-white placeholder-slate-400 focus:outline-none focus:border-accent transition-colors"
            />
          </div>

          {/* Sort Selector & Count */}
          <div className="flex items-center space-x-2 shrink-0">
            <div className="relative flex items-center">
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="pl-8 pr-7 py-2 rounded-xl bg-slate-900 border border-slate-700/80 text-xs text-slate-200 focus:outline-none focus:border-accent appearance-none cursor-pointer"
              >
                <option value="overall">Sort: Rating (High → Low)</option>
                <option value="batting">Sort: Batting Rating</option>
                <option value="bowling">Sort: Bowling Rating</option>
                <option value="name">Sort: Name (A → Z)</option>
              </select>
            </div>

            <div className="px-3 py-2 rounded-xl bg-slate-900/90 border border-slate-800 text-xs font-semibold text-slate-300 flex items-center space-x-1.5 shrink-0">
              <Users className="w-3.5 h-3.5 text-accent" />
              <span>
                {availableCount} / {candidates.length} Open
              </span>
            </div>
          </div>
        </div>

        {/* Role Tabs */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 scrollbar-none">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1 shrink-0 flex items-center space-x-1">
            <Filter className="w-3 h-3" />
            <span>Role:</span>
          </span>
          {ROLE_TABS.map((tab) => (
            <button
              key={tab.role}
              type="button"
              onClick={() => setSelectedRole(tab.role)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-bold transition-all shrink-0",
                selectedRole === tab.role
                  ? "bg-accent text-white shadow-sm"
                  : "bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800/80"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Candidates Grid */}
      {filteredAndSortedPlayers.length === 0 ? (
        <div className="text-center py-12 px-4 rounded-2xl bg-surface/50 border border-slate-800 space-y-2">
          <p className="text-sm font-semibold text-slate-300">No players found</p>
          <p className="text-xs text-slate-400">
            No candidate matches your current search or role filters.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {filteredAndSortedPlayers.map((player) => (
            <CandidateCard
              key={player.player_id}
              player={player}
              isMyTurn={isMyTurn}
              isDrafted={draftedIds.includes(player.player_id)}
              onSelect={onSelectPlayer}
            />
          ))}
        </div>
      )}
    </div>
  );
};


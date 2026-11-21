import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Trophy, Users, Shield, Zap, Search, ArrowRight, Activity } from "lucide-react";
import { Button } from "../components/common/Button";
import { Badge } from "../components/common/Badge";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { usePlayers } from "../hooks/usePlayers";
import { useGame } from "../contexts/GameContext";
import { formatRating } from "../utils/helpers";

export const LandingPage: React.FC = () => {
  const { clearSession } = useGame();
  const [search, setSearch] = useState("");
  const { players, loading, total, updateFilters } = usePlayers({ pageSize: 6 });

  // On Landing Page mount, ensure any previous room/player session is wiped
  useEffect(() => {
    clearSession();
  }, [clearSession]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilters({ search, page: 1 });
  };

  return (
    <div className="space-y-12 sm:space-y-16 py-4 sm:py-6 max-w-6xl mx-auto px-1 sm:px-0">
      {/* Hero Section */}
      <section className="text-center space-y-5 sm:space-y-6 max-w-4xl mx-auto relative">
        {/* Stadium ambient light */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-72 sm:w-96 h-36 sm:h-48 bg-[#0B3D91]/25 blur-3xl pointer-events-none" />

        <div className="inline-flex items-center space-x-2 px-3 sm:px-4 py-1.5 rounded-full bg-[#12263A] border border-[#1E3A5F] text-[#F4C430] text-[10px] sm:text-xs font-black uppercase tracking-wider sm:tracking-widest shadow-md max-w-full">
          <Zap className="w-3.5 h-3.5 text-[#F4C430] shrink-0" />
          <span className="truncate">Real Cricsheet T20 Data • Multiplayer Draft Simulation</span>
        </div>

        <h1 className="text-3xl sm:text-5xl md:text-6xl font-black text-white tracking-tight leading-tight">
          Draft Your Era. <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#F4C430] via-amber-300 to-[#138A36]">
            Simulate The Ultimate XI.
          </span>
        </h1>

        <p className="text-sm sm:text-base md:text-lg text-[#C7D2E2] max-w-2xl mx-auto leading-relaxed px-2 sm:px-0">
          Challenge friends online in real-time. In 11 tactical rounds, draw a random Country & Decade, select from that era's greatest legends, lock batting positions, contest the coin toss, and simulate a full broadcast T20 clash powered by Cricsheet metrics.
        </p>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3.5 sm:gap-4 pt-3 sm:pt-4 w-full max-w-md sm:max-w-none mx-auto px-4 sm:px-0">
          <Link to="/create-room" className="w-full sm:w-auto block">
            <Button variant="gold" size="lg" className="w-full sm:w-auto px-8 py-3.5 text-sm sm:text-base flex items-center justify-center space-x-2 font-black shadow-xl shadow-[#F4C430]/20">
              <Users className="w-5 h-5 text-[#081826]" />
              <span>Create Match Room</span>
            </Button>
          </Link>
          <Link to="/join-room" className="w-full sm:w-auto block">
            <Button variant="secondary" size="lg" className="w-full sm:w-auto px-8 py-3.5 text-sm sm:text-base flex items-center justify-center space-x-2 font-bold bg-[#12263A] border-[#1E3A5F] text-white hover:bg-[#1E3A5F]">
              <span>Join with Friend Code</span>
              <ArrowRight className="w-4 h-4 text-[#F4C430]" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
        <div className="cricket-card p-5 sm:p-6 space-y-3 sm:space-y-3.5 shadow-xl hover:border-[#F4C430]/50 transition-all">
          <div className="w-12 h-12 rounded-xl bg-[#081826] border border-[#1E3A5F] flex items-center justify-center text-[#F4C430] shadow-md">
            <Trophy className="w-6 h-6 stroke-[2.2]" />
          </div>
          <h3 className="text-base sm:text-lg font-black text-white uppercase tracking-wide">11-Round Decade Draft</h3>
          <p className="text-xs sm:text-sm text-[#C7D2E2] leading-relaxed">
            India 1990s, Australia 2010s, West Indies 1980s... Pick one legend per round and lock them into their authentic tactical batting position (1–11).
          </p>
        </div>

        <div className="cricket-card p-5 sm:p-6 space-y-3 sm:space-y-3.5 shadow-xl hover:border-[#138A36]/50 transition-all">
          <div className="w-12 h-12 rounded-xl bg-[#081826] border border-[#1E3A5F] flex items-center justify-center text-[#138A36] shadow-md">
            <Shield className="w-6 h-6 stroke-[2.2]" />
          </div>
          <h3 className="text-base sm:text-lg font-black text-white uppercase tracking-wide">506 Official Legends</h3>
          <p className="text-xs sm:text-sm text-[#C7D2E2] leading-relaxed">
            Verified T20 strike rates, bowling economies, wicket counts, averages, and calculated ratings directly calibrated from official match scorecards.
          </p>
        </div>

        <div className="cricket-card p-5 sm:p-6 space-y-3 sm:space-y-3.5 shadow-xl hover:border-[#0B3D91]/80 transition-all">
          <div className="w-12 h-12 rounded-xl bg-[#081826] border border-[#1E3A5F] flex items-center justify-center text-cyan-400 shadow-md">
            <Activity className="w-6 h-6 stroke-[2.2]" />
          </div>
          <h3 className="text-base sm:text-lg font-black text-white uppercase tracking-wide">Ball-by-Ball Simulation</h3>
          <p className="text-xs sm:text-sm text-[#C7D2E2] leading-relaxed">
            Captains contest the coin toss, elect to bat or bowl first, and watch a dynamic ball-by-ball T20 simulation with full scorecards and live commentary.
          </p>
        </div>
      </section>

      {/* Real Dataset Showcase */}
      <section className="space-y-4 sm:space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-black text-white uppercase tracking-wide">Legends Roster</h2>
            <p className="text-xs sm:text-sm text-[#C7D2E2]">
              Explore {total} legendary players across 11 cricket nations and 5 historic decades.
            </p>
          </div>

          <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-72">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search player name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 sm:py-2.5 bg-[#081826] border border-[#1E3A5F] rounded-xl text-xs sm:text-sm text-white placeholder-slate-400 focus:outline-none focus:border-[#F4C430] transition-colors"
              />
            </div>
            <Button variant="primary" type="submit" size="sm" className="font-black px-4 py-2 sm:py-2.5 shrink-0">
              Search
            </Button>
          </form>
        </div>

        {loading ? (
          <LoadingSpinner label="Querying player database..." />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {players.map((player) => (
              <div key={player.player_id} className="cricket-card p-4 space-y-3 shadow-md hover:border-[#F4C430]/40 transition-all">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-black text-white text-sm sm:text-base">{player.player_name}</h4>
                    <span className="text-[11px] sm:text-xs text-[#C7D2E2] font-medium">{player.country} • {player.decade}s</span>
                  </div>
                  <Badge variant="role" roleType={player.primary_role} className="font-bold text-[10px]">
                    {player.primary_role}
                  </Badge>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#1E3A5F] text-center text-xs">
                  <div className="bg-[#081826] p-2 rounded-xl border border-[#1E3A5F]/70">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">OVR</span>
                    <span className="font-mono font-black text-[#F4C430] text-sm">{formatRating(player.overall_rating)}</span>
                  </div>
                  <div className="bg-[#081826] p-2 rounded-xl border border-[#1E3A5F]/70">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Runs</span>
                    <span className="font-mono font-bold text-white text-sm">{player.runs}</span>
                  </div>
                  <div className="bg-[#081826] p-2 rounded-xl border border-[#1E3A5F]/70">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Wkts</span>
                    <span className="font-mono font-bold text-emerald-400 text-sm">{player.wickets}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

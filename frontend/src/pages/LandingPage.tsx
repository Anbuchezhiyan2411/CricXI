import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Trophy, Users, Shield, Zap, Search, ArrowRight, Activity } from "lucide-react";
import { Button } from "../components/common/Button";
import { Card } from "../components/common/Card";
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
    <div className="space-y-16 py-4">
      {/* Hero Section */}
      <section className="text-center space-y-6 max-w-3xl mx-auto">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-semibold uppercase tracking-wider">
          <Zap className="w-3.5 h-3.5" />
          <span>Real Cricsheet T20 Data • Multiplayer Draft</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-black text-white tracking-tight leading-tight">
          Draft Your Era. <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-emerald-400">
            Simulate The Ultimate XI.
          </span>
        </h1>

        <p className="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto">
          Challenge friends online. In 11 intense rounds, draw a random Country & Decade, select from that era's strongest XI, lock positions, conduct the toss, and simulate a full T20 battle using real player metrics.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link to="/create-room">
            <Button size="lg" className="w-full sm:w-auto px-8 py-3.5 text-base flex items-center space-x-2">
              <Users className="w-5 h-5" />
              <span>Create Room</span>
            </Button>
          </Link>
          <Link to="/join-room">
            <Button variant="secondary" size="lg" className="w-full sm:w-auto px-8 py-3.5 text-base flex items-center space-x-2">
              <span>Join with Friend Code</span>
              <ArrowRight className="w-4 h-4 text-slate-400" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card hoverEffect className="space-y-3">
          <div className="w-10 h-10 rounded-lg bg-accent/20 border border-accent/30 flex items-center justify-center text-accent">
            <Trophy className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white">11-Round Decade Draft</h3>
          <p className="text-sm text-slate-400">
            India 1990, Australia 2010, Pakistan 1980... Pick one legend per round and lock them into their authentic batting position.
          </p>
        </Card>

        <Card hoverEffect className="space-y-3">
          <div className="w-10 h-10 rounded-lg bg-highlight/20 border border-highlight/30 flex items-center justify-center text-highlight">
            <Shield className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white">506 Official Legends</h3>
          <p className="text-sm text-slate-400">
            Accurate T20 strike rates, bowling economies, wicket counts, averages, and calculated ratings directly from Cricsheet.
          </p>
        </Card>

        <Card hoverEffect className="space-y-3">
          <div className="w-10 h-10 rounded-lg bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Activity className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white">Ball-by-Ball Simulation</h3>
          <p className="text-sm text-slate-400">
            Captains contest the toss, choose bat or bowl, and watch a probabilistic ball-by-ball T20 simulation with full scorecards.
          </p>
        </Card>
      </section>

      {/* Real Dataset Showcase */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white">Loaded Player Database</h2>
            <p className="text-sm text-slate-400">
              Browse {total} players from the Cricsheet dataset across 11 nations and 5 decades.
            </p>
          </div>

          <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2 w-full sm:w-auto">
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search player name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-surface border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent"
              />
            </div>
            <Button variant="secondary" type="submit" size="sm">
              Search
            </Button>
          </form>
        </div>

        {loading ? (
          <LoadingSpinner label="Querying player database..." />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {players.map((player) => (
              <Card key={player.player_id} hoverEffect className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-white text-base">{player.player_name}</h4>
                    <span className="text-xs text-slate-400">{player.country} • {player.decade}s</span>
                  </div>
                  <Badge variant="role" roleType={player.primary_role}>
                    {player.primary_role}
                  </Badge>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800 text-center text-xs">
                  <div className="bg-background/60 p-2 rounded">
                    <span className="text-slate-500 block">Rating</span>
                    <span className="font-mono font-bold text-highlight">{formatRating(player.overall_rating)}</span>
                  </div>
                  <div className="bg-background/60 p-2 rounded">
                    <span className="text-slate-500 block">Runs</span>
                    <span className="font-mono font-bold text-slate-200">{player.runs}</span>
                  </div>
                  <div className="bg-background/60 p-2 rounded">
                    <span className="text-slate-500 block">Wickets</span>
                    <span className="font-mono font-bold text-accent">{player.wickets}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};


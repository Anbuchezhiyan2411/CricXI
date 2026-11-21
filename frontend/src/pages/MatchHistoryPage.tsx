import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  History,
  Award,
  Trophy,
  Calendar,
  RefreshCw,
  Search,
  FileText,
  Users,
  ChevronLeft,
  ChevronRight,
  Flame,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { historyService } from "../services/historyService";
import { MatchHistoryItem, MatchHistoryDetail } from "../types/history";
import { ScorecardModal } from "../components/match/ScorecardModal";
import { InningsScorecard } from "../types";

export const MatchHistoryPage: React.FC = () => {
  const [matches, setMatches] = useState<MatchHistoryItem[]>([]);
  const [totalMatches, setTotalMatches] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Search filter
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Scorecard modal state
  const [selectedScorecard, setSelectedScorecard] = useState<{
    isOpen: boolean;
    loading: boolean;
    inn1?: InningsScorecard | null;
    inn2?: InningsScorecard | null;
    title?: string;
  }>({
    isOpen: false,
    loading: false,
  });

  const loadHistory = async (page = 1) => {
    setLoading(true);
    setError(null);
    try {
      const data = await historyService.getMatchHistory(page, 10);
      setMatches(data.items);
      setTotalMatches(data.total);
      setCurrentPage(data.page);
      setTotalPages(data.total_pages);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load match history from SQLite database.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory(currentPage);
  }, [currentPage]);

  const handleOpenScorecard = async (matchId: number, matchTitle: string) => {
    setSelectedScorecard({
      isOpen: true,
      loading: true,
      title: matchTitle,
    });
    try {
      const detail: MatchHistoryDetail = await historyService.getMatchDetail(matchId);
      setSelectedScorecard({
        isOpen: true,
        loading: false,
        inn1: detail.scorecard?.first_innings_scorecard ?? null,
        inn2: detail.scorecard?.second_innings_scorecard ?? null,
        title: matchTitle,
      });
    } catch (err: unknown) {
      console.error("Failed to fetch full scorecard:", err);
      alert("Could not load scorecard: " + (err instanceof Error ? err.message : String(err)));
      setSelectedScorecard((prev) => ({ ...prev, isOpen: false, loading: false }));
    }
  };

  const filteredMatches = useMemo(() => {
    if (!searchTerm.trim()) return matches;
    const term = searchTerm.toLowerCase();
    return matches.filter(
      (m) =>
        m.team1_name.toLowerCase().includes(term) ||
        m.team2_name.toLowerCase().includes(term) ||
        m.room_code.toLowerCase().includes(term) ||
        (m.winner_name && m.winner_name.toLowerCase().includes(term)) ||
        (m.player_of_the_match && m.player_of_the_match.toLowerCase().includes(term))
    );
  }, [matches, searchTerm]);

  return (
    <div className="min-h-screen bg-[#081826] text-[#C7D2E2] pb-24">
      {/* Top Header Banner */}
      <div className="bg-gradient-to-b from-[#0B2238] to-[#081826] border-b border-[#1E3A5F]/70 py-8 px-4 sm:px-6 lg:px-8 shadow-2xl relative overflow-hidden">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center space-x-3 mb-2">
              <span className="px-3 py-1 rounded-full text-[11px] font-black uppercase tracking-widest bg-[#12263A] border border-[#1E3A5F] text-[#F4C430] flex items-center gap-1.5">
                <History className="w-3.5 h-3.5 text-[#F4C430]" />
                Official Archives
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#138A36]/20 text-[#138A36] border border-[#138A36]/40">
                SQLite Authoritative Persistence
              </span>
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white font-display tracking-tight">
              Match <span className="text-[#F4C430]">History</span>
            </h1>
            <p className="mt-2 text-sm sm:text-base text-[#8DA4C4] max-w-2xl leading-relaxed">
              Historical records, verified scorecards, and MVP accolades from completed CricXI T20 simulations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="px-4 py-2.5 rounded-xl bg-[#0D2238] border border-[#1E3A5F] text-xs font-bold text-white flex items-center gap-2">
              <Flame className="w-4 h-4 text-[#F4C430]" />
              <span>
                <strong className="text-[#F4C430] font-mono text-sm">{totalMatches}</strong> Completed Matches
              </span>
            </div>

            <button
              onClick={() => loadHistory(currentPage)}
              disabled={loading}
              className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-[#12263A] hover:bg-[#1E3A5F] border border-[#1E3A5F] text-xs font-bold uppercase tracking-wider text-white transition-all shadow-md disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-[#F4C430] ${loading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="max-w-7xl mx-auto mt-6 pt-4 border-t border-[#1E3A5F]/50 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="relative w-full sm:w-96">
            <Search className="w-4 h-4 text-[#8DA4C4] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Filter by team, room code, MVP..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-[#081826] border border-[#1E3A5F] text-xs text-white placeholder-[#8DA4C4] focus:outline-none focus:border-[#F4C430]"
            />
          </div>

          {totalPages > 1 && (
            <div className="flex items-center space-x-2 text-xs font-bold">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1 || loading}
                className="p-2 rounded-lg bg-[#081826] border border-[#1E3A5F] text-[#8DA4C4] hover:text-white disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-[#8DA4C4]">
                Page <strong className="text-white">{currentPage}</strong> of <strong className="text-white">{totalPages}</strong>
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages || loading}
                className="p-2 rounded-lg bg-[#081826] border border-[#1E3A5F] text-[#8DA4C4] hover:text-white disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8 space-y-6">
        {/* Error notification */}
        {error && (
          <div className="p-4 rounded-xl bg-red-950/60 border border-red-500/50 text-red-200 text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              <span>{error}</span>
            </div>
            <button onClick={() => loadHistory(currentPage)} className="underline font-bold text-white text-xs">
              Retry
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="p-16 text-center space-y-3 bg-[#0D2238] border border-[#1E3A5F] rounded-2xl shadow-xl">
            <div className="w-10 h-10 border-4 border-[#1E3A5F] border-t-[#F4C430] rounded-full animate-spin mx-auto" />
            <p className="text-sm font-bold text-white font-display">Loading Match Archives from SQLite...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && filteredMatches.length === 0 && (
          <div className="bg-[#0D2238] border border-[#1E3A5F] rounded-2xl p-12 text-center max-w-2xl mx-auto space-y-6 shadow-2xl">
            <div className="w-20 h-20 bg-[#12263A] rounded-2xl border border-[#1E3A5F] flex items-center justify-center mx-auto text-[#F4C430]">
              <History className="w-10 h-10" />
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-black text-white font-display">No Matches Recorded Yet</h2>
              <p className="text-sm text-[#8DA4C4]">
                Completed games from T20 match simulations will automatically persist into SQLite and be displayed here.
              </p>
            </div>
            <Link
              to="/lobby"
              className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[#0B3D91] to-[#138A36] text-white font-bold text-xs uppercase tracking-wider shadow-lg hover:brightness-110 transition-all"
            >
              <Users className="w-4 h-4" />
              <span>Play Match in Lobby</span>
            </Link>
          </div>
        )}

        {/* Match Cards Listing */}
        {!loading && filteredMatches.length > 0 && (
          <div className="grid grid-cols-1 gap-5">
            {filteredMatches.map((m) => {
              const formattedDate = m.match_date
                ? new Date(m.match_date).toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "Recent Match";

              return (
                <div
                  key={m.id}
                  className="bg-[#0D2238] border border-[#1E3A5F] hover:border-[#F4C430]/40 rounded-2xl p-5 sm:p-6 shadow-xl transition-all relative overflow-hidden group"
                >
                  <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-[#1E3A5F]/70">
                    <div className="flex items-center space-x-3">
                      <span className="px-2.5 py-1 rounded-md text-[10px] font-mono font-black uppercase bg-[#12263A] border border-[#1E3A5F] text-[#F4C430]">
                        Room: {m.room_code}
                      </span>
                      <span className="flex items-center gap-1.5 text-xs text-[#8DA4C4]">
                        <Calendar className="w-3.5 h-3.5" />
                        {formattedDate}
                      </span>
                    </div>

                    <div className="flex items-center space-x-3">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase bg-[#138A36]/20 text-[#138A36] border border-[#138A36]/40 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> {m.status}
                      </span>
                      <button
                        onClick={() => handleOpenScorecard(m.id, `${m.team1_name} vs ${m.team2_name}`)}
                        className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-[#12263A] hover:bg-[#0B3D91] border border-[#1E3A5F] text-xs font-bold text-white transition-all shadow"
                      >
                        <FileText className="w-3.5 h-3.5 text-[#F4C430]" />
                        <span>View Full Scorecard</span>
                      </button>
                    </div>
                  </div>

                  {/* Teams & Scores Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4 items-center">
                    {/* Scores Section */}
                    <div className="space-y-3">
                      {/* Team 1 */}
                      <div className="flex items-center justify-between p-3 rounded-xl bg-[#081826] border border-[#1E3A5F]">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 rounded-lg bg-[#0B3D91]/30 border border-[#0B3D91] flex items-center justify-center font-black text-xs text-[#F4C430]">
                            1
                          </div>
                          <div>
                            <div className="text-sm font-black text-white">{m.team1_name}</div>
                            <div className="text-[10px] text-[#8DA4C4]">
                              {m.innings1?.team_user_id === m.team1_user_id ? "Batted 1st" : "Chased 2nd"}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-base font-black font-mono text-white">
                            {m.innings1?.team_user_id === m.team1_user_id
                              ? m.innings1?.display_score
                              : m.innings2?.display_score || "DNB"}
                          </div>
                          <div className="text-[10px] font-mono text-[#8DA4C4]">
                            RR:{" "}
                            {m.innings1?.team_user_id === m.team1_user_id
                              ? m.innings1?.run_rate.toFixed(2)
                              : m.innings2?.run_rate.toFixed(2) || "0.00"}
                          </div>
                        </div>
                      </div>

                      {/* Team 2 */}
                      <div className="flex items-center justify-between p-3 rounded-xl bg-[#081826] border border-[#1E3A5F]">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 rounded-lg bg-[#138A36]/30 border border-[#138A36] flex items-center justify-center font-black text-xs text-[#138A36]">
                            2
                          </div>
                          <div>
                            <div className="text-sm font-black text-white">{m.team2_name}</div>
                            <div className="text-[10px] text-[#8DA4C4]">
                              {m.innings1?.team_user_id === m.team2_user_id ? "Batted 1st" : "Chased 2nd"}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-base font-black font-mono text-white">
                            {m.innings1?.team_user_id === m.team2_user_id
                              ? m.innings1?.display_score
                              : m.innings2?.display_score || "DNB"}
                          </div>
                          <div className="text-[10px] font-mono text-[#8DA4C4]">
                            RR:{" "}
                            {m.innings1?.team_user_id === m.team2_user_id
                              ? m.innings1?.run_rate.toFixed(2)
                              : m.innings2?.run_rate.toFixed(2) || "0.00"}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Outcome & MVP Banner */}
                    <div className="space-y-3 bg-[#081826] border border-[#1E3A5F] rounded-xl p-4 flex flex-col justify-between h-full">
                      <div>
                        <div className="text-[10px] font-bold text-[#8DA4C4] uppercase">Match Result</div>
                        <div className="text-base font-black text-[#F4C430] flex items-center gap-2 mt-1">
                          <Trophy className="w-4 h-4 text-[#F4C430] flex-shrink-0" />
                          <span>{m.result_margin || (m.winner_name ? `${m.winner_name} won!` : "Match Completed")}</span>
                        </div>
                        {m.toss_winner_name && (
                          <div className="text-xs text-[#8DA4C4] mt-1.5">
                            Toss: <strong className="text-white">{m.toss_winner_name}</strong> elected to{" "}
                            <strong className="text-white">{m.toss_decision || "BAT"}</strong>
                          </div>
                        )}
                      </div>

                      {m.player_of_the_match && (
                        <div className="pt-3 border-t border-[#1E3A5F]/80 flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <Award className="w-4 h-4 text-[#F4C430]" />
                            <div>
                              <span className="text-[10px] font-bold text-[#8DA4C4] uppercase block">
                                Player of the Match
                              </span>
                              <span className="text-xs font-black text-white">{m.player_of_the_match}</span>
                            </div>
                          </div>
                          {m.player_of_the_match_details && (
                            <span className="text-xs font-mono text-[#38BDF8] bg-[#12263A] px-2 py-0.5 rounded border border-[#1E3A5F]">
                              {m.player_of_the_match_details}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t border-[#1E3A5F]/50">
            <span className="text-xs text-[#8DA4C4]">
              Showing <strong className="text-white">{filteredMatches.length}</strong> of{" "}
              <strong className="text-white">{totalMatches}</strong> total records
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1 || loading}
                className="px-3 py-1.5 rounded-lg bg-[#0D2238] border border-[#1E3A5F] text-xs font-bold text-white hover:bg-[#1E3A5F] disabled:opacity-40"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages || loading}
                className="px-3 py-1.5 rounded-lg bg-[#0D2238] border border-[#1E3A5F] text-xs font-bold text-white hover:bg-[#1E3A5F] disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Full Scorecard Modal */}
      <ScorecardModal
        isOpen={selectedScorecard.isOpen}
        onClose={() => setSelectedScorecard((prev) => ({ ...prev, isOpen: false }))}
        inn1={selectedScorecard.inn1}
        inn2={selectedScorecard.inn2}
      />
    </div>
  );
};

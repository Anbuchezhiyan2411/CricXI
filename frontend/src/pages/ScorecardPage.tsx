import React, { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Trophy,
  Award,
  FileText,
  Users,
  BarChart3,
  History,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { matchService } from "../services/matchService";
import { historyService } from "../services/historyService";
import { LiveMatchStateResponse, InningsScorecard } from "../types";
import { useGame } from "../contexts/GameContext";

export const ScorecardPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { currentRoom } = useGame();

  const roomParam = searchParams.get("room") || currentRoom?.room_code || localStorage.getItem("cricxi_room_code") || "";
  const matchParam = searchParams.get("match") || "";

  const [matchState, setMatchState] = useState<LiveMatchStateResponse | null>(null);
  const [activeInningsTab, setActiveInningsTab] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadScorecard = async () => {
      setLoading(true);
      setError(null);

      try {
        if (roomParam) {
          const code = roomParam.trim().toUpperCase();
          let state = await matchService.getMatchState(code);

          // If match in this room is not yet marked completed, simulate to completion
          if (state.status !== "COMPLETED" && state.status !== "TIED") {
            setSimulating(true);
            state = await matchService.simulateMatch(code);
            setSimulating(false);
          }

          setMatchState(state);
          setActiveInningsTab(state.second_innings_scorecard ? 2 : 1);
        } else if (matchParam) {
          const detail = await historyService.getMatchDetail(Number(matchParam));
          if (detail.scorecard) {
            setMatchState(detail.scorecard);
            setActiveInningsTab(detail.scorecard.second_innings_scorecard ? 2 : 1);
          } else {
            setError("Full scorecard data not available for this match.");
          }
        } else {
          // Fallback to most recent completed match in history
          const history = await historyService.getMatchHistory(1, 1);
          if (history.items.length > 0) {
            const detail = await historyService.getMatchDetail(history.items[0].id);
            if (detail.scorecard) {
              setMatchState(detail.scorecard);
              setActiveInningsTab(detail.scorecard.second_innings_scorecard ? 2 : 1);
            }
          } else {
            setError("No completed match found. Please complete a match to view its scorecard.");
          }
        }
      } catch (err: unknown) {
        console.error("Failed to load scorecard:", err);
        const msg = err instanceof Error ? err.message : "Failed to load match scorecard.";
        setError(msg);
      } finally {
        setLoading(false);
        setSimulating(false);
      }
    };

    loadScorecard();
  }, [roomParam, matchParam]);

  if (loading || simulating) {
    return (
      <div className="min-h-screen bg-[#081826] text-white flex flex-col items-center justify-center p-6 space-y-4">
        <div className="w-16 h-16 border-4 border-[#1E3A5F] border-t-[#F4C430] rounded-full animate-spin" />
        <div className="text-center space-y-1">
          <h2 className="text-xl font-black font-display text-white tracking-wide">
            {simulating ? "Simulating Match..." : "Loading Official Scorecard..."}
          </h2>
          <p className="text-xs text-[#8DA4C4]">
            {simulating
              ? "Calculating deliveries, wickets, and official figures in the background"
              : "Reconciling innings statistics, batter figures, and bowling economies"}
          </p>
        </div>
      </div>
    );
  }

  if (error || !matchState) {
    return (
      <div className="min-h-screen bg-[#081826] text-[#C7D2E2] flex items-center justify-center p-4">
        <div className="bg-[#0D2238] border border-[#1E3A5F] rounded-2xl p-8 max-w-md w-full text-center space-y-5 shadow-2xl">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
          <div className="space-y-1">
            <h2 className="text-xl font-black text-white font-display">Scorecard Notice</h2>
            <p className="text-xs text-[#8DA4C4] leading-relaxed">{error || "Match scorecard not found."}</p>
          </div>
          <div className="flex justify-center gap-3 pt-2">
            <Link
              to="/lobby"
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#0B3D91] to-[#138A36] text-white font-bold text-xs uppercase tracking-wider shadow"
            >
              Go to Lobby
            </Link>
            <Link
              to="/history"
              className="px-5 py-2.5 rounded-xl bg-[#12263A] border border-[#1E3A5F] text-white font-bold text-xs uppercase tracking-wider hover:bg-[#1E3A5F]"
            >
              Match History
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const inn1 = matchState.first_innings_scorecard;
  const inn2 = matchState.second_innings_scorecard;
  const activeInnings: InningsScorecard | null | undefined = activeInningsTab === 1 ? inn1 : inn2;

  return (
    <div className="min-h-screen bg-[#081826] text-[#C7D2E2] pb-24">
      {/* Top Banner */}
      <div className="bg-gradient-to-b from-[#0B2238] to-[#081826] border-b border-[#1E3A5F]/70 py-8 px-4 sm:px-6 lg:px-8 shadow-2xl relative overflow-hidden">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center space-x-3 mb-2">
              <span className="px-3 py-1 rounded-full text-[11px] font-black uppercase tracking-widest bg-[#12263A] border border-[#1E3A5F] text-[#F4C430] flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-[#F4C430]" />
                Official T20 Scorecard
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#138A36]/20 text-[#138A36] border border-[#138A36]/40 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Match Completed
              </span>
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-white font-display tracking-tight">
              {matchState.host_team.team_name} <span className="text-[#F4C430]">vs</span> {matchState.guest_team.team_name}
            </h1>
            <p className="mt-2 text-xs sm:text-sm text-[#8DA4C4]">
              Room Code: <strong className="text-white font-mono">{matchState.room_code}</strong> | Match #{matchState.match_id}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/history"
              className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-[#12263A] hover:bg-[#1E3A5F] border border-[#1E3A5F] text-xs font-bold uppercase tracking-wider text-white transition-all shadow-md"
            >
              <History className="w-3.5 h-3.5 text-[#F4C430]" />
              <span>Match Archives</span>
            </Link>
            <Link
              to="/analytics"
              className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-[#12263A] hover:bg-[#1E3A5F] border border-[#1E3A5F] text-xs font-bold uppercase tracking-wider text-white transition-all shadow-md"
            >
              <BarChart3 className="w-3.5 h-3.5 text-[#38BDF8]" />
              <span>Analytics</span>
            </Link>
            <Link
              to="/lobby"
              className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#0B3D91] to-[#138A36] hover:brightness-110 text-xs font-black uppercase tracking-wider text-white transition-all shadow-lg shadow-[#0B3D91]/30"
            >
              <Users className="w-3.5 h-3.5 text-[#F4C430]" />
              <span>Play Another Match</span>
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mt-8 space-y-6">
        {/* Match Result & MVP Card */}
        <div className="bg-[#0D2238] border-2 border-[#1E3A5F] rounded-2xl p-6 shadow-2xl relative overflow-hidden">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center space-x-2 text-[#F4C430]">
                <Trophy className="w-5 h-5 text-[#F4C430]" />
                <span className="text-xs font-black uppercase tracking-widest text-[#F4C430]">Result</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-white font-display">
                {matchState.result_margin || (matchState.winner_name ? `${matchState.winner_name} won!` : "Match Tied")}
              </h2>
            </div>

            {matchState.player_of_the_match && (
              <div className="bg-[#081826] border border-[#1E3A5F] rounded-xl px-4 py-3 flex items-center space-x-3 self-stretch md:self-auto">
                <div className="w-10 h-10 rounded-xl bg-[#F4C430]/15 flex items-center justify-center text-[#F4C430]">
                  <Award className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-bold text-[#8DA4C4] uppercase">Player of the Match</div>
                  <div className="text-sm font-black text-white">{matchState.player_of_the_match}</div>
                  {matchState.player_of_the_match_details && (
                    <div className="text-xs font-mono text-[#38BDF8]">{matchState.player_of_the_match_details}</div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Quick Innings Score Pills */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6 pt-6 border-t border-[#1E3A5F]/70">
            {inn1 && (
              <div
                onClick={() => setActiveInningsTab(1)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                  activeInningsTab === 1
                    ? "bg-[#12263A] border-[#F4C430]/50 shadow-md"
                    : "bg-[#081826] border-[#1E3A5F] opacity-75 hover:opacity-100"
                }`}
              >
                <div>
                  <div className="text-xs font-black text-white">{inn1.batting_team_name}</div>
                  <div className="text-[10px] text-[#8DA4C4]">1st Innings</div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-black font-mono text-[#F4C430]">
                    {inn1.total_runs}/{inn1.total_wickets}
                  </div>
                  <div className="text-[10px] font-mono text-[#8DA4C4]">({inn1.total_overs.toFixed(1)} ov)</div>
                </div>
              </div>
            )}

            {inn2 && (
              <div
                onClick={() => setActiveInningsTab(2)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                  activeInningsTab === 2
                    ? "bg-[#12263A] border-[#F4C430]/50 shadow-md"
                    : "bg-[#081826] border-[#1E3A5F] opacity-75 hover:opacity-100"
                }`}
              >
                <div>
                  <div className="text-xs font-black text-white">{inn2.batting_team_name}</div>
                  <div className="text-[10px] text-[#8DA4C4]">2nd Innings</div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-black font-mono text-[#38BDF8]">
                    {inn2.total_runs}/{inn2.total_wickets}
                  </div>
                  <div className="text-[10px] font-mono text-[#8DA4C4]">({inn2.total_overs.toFixed(1)} ov)</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Innings Tabs Switcher */}
        <div className="flex border-b border-[#1E3A5F] gap-2">
          {inn1 && (
            <button
              onClick={() => setActiveInningsTab(1)}
              className={`px-5 py-3 text-xs font-black uppercase tracking-wider border-b-2 transition-all flex items-center gap-2 ${
                activeInningsTab === 1
                  ? "border-[#F4C430] text-[#F4C430] bg-[#12263A]/40"
                  : "border-transparent text-[#8DA4C4] hover:text-white"
              }`}
            >
              <span>1st Innings: {inn1.batting_team_name}</span>
              <span className="font-mono text-white">({inn1.total_runs}/{inn1.total_wickets})</span>
            </button>
          )}

          {inn2 && (
            <button
              onClick={() => setActiveInningsTab(2)}
              className={`px-5 py-3 text-xs font-black uppercase tracking-wider border-b-2 transition-all flex items-center gap-2 ${
                activeInningsTab === 2
                  ? "border-[#F4C430] text-[#F4C430] bg-[#12263A]/40"
                  : "border-transparent text-[#8DA4C4] hover:text-white"
              }`}
            >
              <span>2nd Innings: {inn2.batting_team_name}</span>
              <span className="font-mono text-white">({inn2.total_runs}/{inn2.total_wickets})</span>
            </button>
          )}
        </div>

        {/* Detailed Innings Scorecard */}
        {activeInnings && (
          <div className="space-y-6">
            {/* Batting Card */}
            <div className="bg-[#0D2238] border border-[#1E3A5F] rounded-2xl overflow-hidden shadow-xl">
              <div className="p-4 bg-[#12263A] border-b border-[#1E3A5F] flex items-center justify-between">
                <h3 className="text-xs font-black uppercase tracking-wider text-white">
                  Batting — {activeInnings.batting_team_name}
                </h3>
                <span className="text-xs font-mono text-[#F4C430] font-bold">
                  {activeInnings.total_runs}/{activeInnings.total_wickets} ({activeInnings.total_overs.toFixed(1)} ov)
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-[#081826] text-[#8DA4C4] font-bold uppercase tracking-wider border-b border-[#1E3A5F]/70">
                      <th className="py-2.5 px-4">Batter</th>
                      <th className="py-2.5 px-4">Dismissal</th>
                      <th className="py-2.5 px-3 text-center">R</th>
                      <th className="py-2.5 px-3 text-center">B</th>
                      <th className="py-2.5 px-3 text-center">4s</th>
                      <th className="py-2.5 px-3 text-center">6s</th>
                      <th className="py-2.5 px-3 text-center">SR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1E3A5F]/40 bg-[#0D2238]">
                    {activeInnings.batters.map((b) => (
                      <tr key={b.player_id} className="hover:bg-[#12263A]/60 transition-colors">
                        <td className="py-2.5 px-4 font-bold text-white flex items-center gap-2">
                          <span>{b.player_name}</span>
                          {b.decade && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#081826] border border-[#1E3A5F] text-[#8DA4C4]">
                              {b.decade}s
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-4 text-[#8DA4C4] font-mono text-[11px]">{b.dismissal_text}</td>
                        <td className="py-2.5 px-3 text-center font-bold text-white font-mono">{b.runs}</td>
                        <td className="py-2.5 px-3 text-center font-mono text-[#8DA4C4]">{b.balls}</td>
                        <td className="py-2.5 px-3 text-center font-mono text-[#8DA4C4]">{b.fours}</td>
                        <td className="py-2.5 px-3 text-center font-mono text-[#8DA4C4]">{b.sixes}</td>
                        <td className="py-2.5 px-3 text-center font-bold font-mono text-[#F4C430]">
                          {b.strike_rate.toFixed(1)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-[#081826] text-white font-bold border-t border-[#1E3A5F]">
                      <td colSpan={2} className="py-2.5 px-4 text-[#8DA4C4]">
                        Extras: (w {activeInnings.wides}, nb {activeInnings.no_balls}, b {activeInnings.byes}, lb {activeInnings.leg_byes})
                      </td>
                      <td colSpan={5} className="py-2.5 px-3 text-right font-mono text-[#F4C430] pr-4">
                        {activeInnings.extras} runs
                      </td>
                    </tr>
                    <tr className="bg-[#12263A] text-white font-black border-t-2 border-[#1E3A5F]">
                      <td colSpan={2} className="py-3 px-4 uppercase text-xs">
                        Total
                      </td>
                      <td colSpan={5} className="py-3 px-3 text-right font-mono text-base text-[#F4C430] pr-4">
                        {activeInnings.total_runs}/{activeInnings.total_wickets} ({activeInnings.total_overs.toFixed(1)} ov, RR: {(activeInnings.total_runs / Math.max(0.1, activeInnings.legal_balls_bowled / 6)).toFixed(2)})
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Fall of Wickets */}
            {activeInnings.fall_of_wickets && activeInnings.fall_of_wickets.length > 0 && (
              <div className="bg-[#0D2238] border border-[#1E3A5F] rounded-2xl p-4 shadow-xl">
                <h4 className="text-xs font-black uppercase tracking-wider text-[#8DA4C4] mb-3">Fall of Wickets</h4>
                <div className="flex flex-wrap gap-2">
                  {activeInnings.fall_of_wickets.map((fow, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 rounded-lg bg-[#081826] border border-[#1E3A5F] text-xs font-mono text-white"
                    >
                      {fow}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Bowling Card */}
            <div className="bg-[#0D2238] border border-[#1E3A5F] rounded-2xl overflow-hidden shadow-xl">
              <div className="p-4 bg-[#12263A] border-b border-[#1E3A5F] flex items-center justify-between">
                <h3 className="text-xs font-black uppercase tracking-wider text-white">
                  Bowling — {activeInnings.bowling_team_name}
                </h3>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-[#081826] text-[#8DA4C4] font-bold uppercase tracking-wider border-b border-[#1E3A5F]/70">
                      <th className="py-2.5 px-4">Bowler</th>
                      <th className="py-2.5 px-3 text-center">O</th>
                      <th className="py-2.5 px-3 text-center">M</th>
                      <th className="py-2.5 px-3 text-center">R</th>
                      <th className="py-2.5 px-3 text-center">W</th>
                      <th className="py-2.5 px-3 text-center">ECON</th>
                      <th className="py-2.5 px-3 text-center">WD</th>
                      <th className="py-2.5 px-3 text-center">NB</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1E3A5F]/40 bg-[#0D2238]">
                    {activeInnings.bowlers.map((bw) => (
                      <tr key={bw.player_id} className="hover:bg-[#12263A]/60 transition-colors">
                        <td className="py-2.5 px-4 font-bold text-white flex items-center gap-2">
                          <span>{bw.player_name}</span>
                          {bw.decade && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#081826] border border-[#1E3A5F] text-[#8DA4C4]">
                              {bw.decade}s
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono font-bold text-white">{bw.overs.toFixed(1)}</td>
                        <td className="py-2.5 px-3 text-center font-mono text-[#8DA4C4]">{bw.maidens}</td>
                        <td className="py-2.5 px-3 text-center font-mono text-[#8DA4C4]">{bw.runs_conceded}</td>
                        <td className="py-2.5 px-3 text-center font-mono font-black text-[#138A36] text-sm">
                          {bw.wickets}
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono text-[#F4C430] font-bold">
                          {bw.economy.toFixed(2)}
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono text-[#8DA4C4]">{bw.wides}</td>
                        <td className="py-2.5 px-3 text-center font-mono text-[#8DA4C4]">{bw.no_balls}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

import React, { useState } from "react";
import { X, FileText } from "lucide-react";
import { InningsScorecard } from "../../types";

interface ScorecardModalProps {
  isOpen: boolean;
  onClose: () => void;
  inn1?: InningsScorecard | null;
  inn2?: InningsScorecard | null;
}

export const ScorecardModal: React.FC<ScorecardModalProps> = ({
  isOpen,
  onClose,
  inn1,
  inn2,
}) => {
  const [activeTab, setActiveTab] = useState<number>(inn2 ? 2 : 1);

  if (!isOpen) return null;

  const currentScorecard = activeTab === 1 ? inn1 : inn2;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-[#081826]/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-3xl bg-[#12263A] border-2 border-[#1E3A5F] shadow-2xl overflow-hidden text-white">
        {/* Glow accent */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#0B3D91] via-[#F4C430] to-[#138A36]" />

        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#1E3A5F] bg-[#12263A]">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#F4C430]/15 flex items-center justify-center text-[#F4C430]">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-lg font-black text-white uppercase tracking-wider">
                Official Match Scorecard
              </h3>
              <p className="text-xs text-[#C7D2E2]">
                Detailed batting, bowling figures, extras, and fall of wickets
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-xl bg-[#081826] hover:bg-[#1E3A5F] text-slate-400 hover:text-white flex items-center justify-center transition-colors border border-[#1E3A5F]"
            aria-label="Close Scorecard"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Innings Tabs */}
        <div className="flex border-b border-[#1E3A5F] bg-[#081826] px-5 pt-3 space-x-2">
          {inn1 && (
            <button
              onClick={() => setActiveTab(1)}
              className={`pb-3 px-4 text-xs font-black uppercase tracking-wider transition-all border-b-2 ${
                activeTab === 1
                  ? "border-[#F4C430] text-[#F4C430]"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              1st Innings: {inn1.batting_team_name} ({inn1.total_runs}/{inn1.total_wickets})
            </button>
          )}

          {inn2 && (
            <button
              onClick={() => setActiveTab(2)}
              className={`pb-3 px-4 text-xs font-black uppercase tracking-wider transition-all border-b-2 ${
                activeTab === 2
                  ? "border-[#F4C430] text-[#F4C430]"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              2nd Innings: {inn2.batting_team_name} ({inn2.total_runs}/{inn2.total_wickets})
            </button>
          )}
        </div>

        {/* Content Body */}
        <div className="overflow-y-auto p-5 space-y-6">
          {currentScorecard ? (
            <>
              {/* Batting Scorecard Table */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-black uppercase tracking-wider text-[#F4C430]">
                    Batting • {currentScorecard.batting_team_name}
                  </h4>
                  <span className="text-xs font-black text-white bg-[#081826] px-3 py-1 rounded-lg border border-[#1E3A5F]">
                    Total: {currentScorecard.total_runs}/{currentScorecard.total_wickets} (
                    {currentScorecard.total_overs.toFixed(1)} Ov)
                  </span>
                </div>

                <div className="rounded-xl border border-[#1E3A5F] overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#081826] text-slate-400 font-bold border-b border-[#1E3A5F] text-[11px] uppercase tracking-wider">
                      <tr>
                        <th className="py-2.5 px-3">#</th>
                        <th className="py-2.5 px-3">Batter</th>
                        <th className="py-2.5 px-3">Dismissal</th>
                        <th className="py-2.5 px-2 text-right">R</th>
                        <th className="py-2.5 px-2 text-right">B</th>
                        <th className="py-2.5 px-2 text-right">4s</th>
                        <th className="py-2.5 px-2 text-right">6s</th>
                        <th className="py-2.5 px-3 text-right">SR</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1E3A5F]/50">
                      {currentScorecard.batters.map((b) => (
                        <tr key={b.player_id} className="text-slate-200 hover:bg-[#1E3A5F]/30">
                          <td className="py-2.5 px-3 text-slate-400 font-mono">
                            {b.batting_position}
                          </td>
                          <td className="py-2.5 px-3 font-bold text-white flex items-center space-x-1.5">
                            <span>{b.player_name}</span>
                            {b.decade ? (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#081826] text-amber-400 font-mono font-medium border border-[#1E3A5F]">
                                {b.decade}s
                              </span>
                            ) : null}
                          </td>
                          <td className="py-2.5 px-3 text-[11px]">
                            {b.is_out ? (
                              <span className="text-slate-300 italic">{b.dismissal_text}</span>
                            ) : b.has_batted ? (
                              <span className="text-emerald-400 font-black not-italic">not out</span>
                            ) : (
                              <span className="text-slate-500 font-semibold not-italic">DNB</span>
                            )}
                          </td>
                          <td className="py-2.5 px-2 text-right font-black text-[#F4C430] font-mono">
                            {b.has_batted ? b.runs : "-"}
                          </td>
                          <td className="py-2.5 px-2 text-right text-[#C7D2E2] font-mono">
                            {b.has_batted ? b.balls : "-"}
                          </td>
                          <td className="py-2.5 px-2 text-right text-slate-400 font-mono">
                            {b.has_batted ? b.fours : "-"}
                          </td>
                          <td className="py-2.5 px-2 text-right text-slate-400 font-mono">
                            {b.has_batted ? b.sixes : "-"}
                          </td>
                          <td className="py-2.5 px-3 text-right font-black text-emerald-400 font-mono">
                            {b.has_batted && b.balls > 0 ? b.strike_rate.toFixed(1) : "-"}
                          </td>
                        </tr>
                      ))}

                      {/* Extras Row */}
                      <tr className="bg-[#081826]/70 font-medium text-[#C7D2E2] border-t border-[#1E3A5F]">
                        <td colSpan={3} className="py-2.5 px-3">
                          Extras{" "}
                          <span className="text-[11px] text-slate-400 font-mono">
                            (w {currentScorecard.wides ?? 0}, nb {currentScorecard.no_balls ?? 0}, b {currentScorecard.byes ?? 0}, lb {currentScorecard.leg_byes ?? 0})
                          </span>
                        </td>
                        <td className="py-2.5 px-2 text-right font-black text-white font-mono">
                          {currentScorecard.extras ?? 0}
                        </td>
                        <td colSpan={4}></td>
                      </tr>

                      {/* Innings Total Row */}
                      <tr className="bg-[#081826] font-black text-white border-t-2 border-[#1E3A5F]">
                        <td colSpan={3} className="py-3 px-3 uppercase tracking-wider text-[#F4C430]">
                          Total ({currentScorecard.total_wickets} wkts, {currentScorecard.total_overs.toFixed(1)} Ov)
                        </td>
                        <td className="py-3 px-2 text-right text-base text-[#F4C430] font-black font-mono">
                          {currentScorecard.total_runs}
                        </td>
                        <td colSpan={4} className="py-3 px-3 text-right text-[#C7D2E2] font-mono text-xs">
                          RR: {(
                            (currentScorecard.total_runs / Math.max(1, currentScorecard.legal_balls_bowled)) *
                            6
                          ).toFixed(2)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Did Not Bat Summary */}
                {currentScorecard.batters.some((b) => !b.has_batted) && (
                  <div className="text-xs text-[#C7D2E2] px-3.5 py-2.5 rounded-xl bg-[#081826] border border-[#1E3A5F] flex flex-wrap gap-1.5 items-center">
                    <span className="font-black text-slate-400 uppercase tracking-wider text-[10px] mr-1">
                      Did Not Bat:
                    </span>
                    {currentScorecard.batters
                      .filter((b) => !b.has_batted)
                      .map((b, idx, arr) => (
                        <span key={b.player_id} className="text-white font-medium">
                          {b.player_name}
                          {b.decade ? ` (${b.decade}s)` : ""}
                          {idx < arr.length - 1 ? "," : ""}
                        </span>
                      ))}
                  </div>
                )}
              </div>

              {/* Bowling Scorecard Table */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-black uppercase tracking-wider text-cyan-400">
                    Bowling • {currentScorecard.bowling_team_name}
                  </h4>
                </div>

                <div className="rounded-xl border border-[#1E3A5F] overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#081826] text-slate-400 font-bold border-b border-[#1E3A5F] text-[11px] uppercase tracking-wider">
                      <tr>
                        <th className="py-2.5 px-3">Bowler</th>
                        <th className="py-2.5 px-2 text-right">O</th>
                        <th className="py-2.5 px-2 text-right">M</th>
                        <th className="py-2.5 px-2 text-right">R</th>
                        <th className="py-2.5 px-2 text-right">W</th>
                        <th className="py-2.5 px-2 text-right">Wd</th>
                        <th className="py-2.5 px-2 text-right">Nb</th>
                        <th className="py-2.5 px-3 text-right">Econ</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1E3A5F]/50">
                      {currentScorecard.bowlers.map((bw) => (
                        <tr key={bw.player_id} className="text-slate-200 hover:bg-[#1E3A5F]/30">
                          <td className="py-2.5 px-3 font-bold text-cyan-300 flex items-center space-x-1.5">
                            <span>{bw.player_name}</span>
                            {bw.decade ? (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#081826] text-cyan-300 font-mono font-medium border border-[#1E3A5F]">
                                {bw.decade}s
                              </span>
                            ) : null}
                          </td>
                          <td className="py-2.5 px-2 text-right text-white font-bold font-mono">
                            {bw.overs.toFixed(1)}
                          </td>
                          <td className="py-2.5 px-2 text-right text-slate-400 font-mono">
                            {bw.maidens}
                          </td>
                          <td className="py-2.5 px-2 text-right text-slate-300 font-mono">
                            {bw.runs_conceded}
                          </td>
                          <td className="py-2.5 px-2 text-right font-black text-[#F4C430] text-sm font-mono">
                            {bw.wickets}
                          </td>
                          <td className="py-2.5 px-2 text-right text-slate-400 font-mono">
                            {bw.wides}
                          </td>
                          <td className="py-2.5 px-2 text-right text-slate-400 font-mono">
                            {bw.no_balls}
                          </td>
                          <td className="py-2.5 px-3 text-right font-black text-cyan-400 font-mono">
                            {bw.economy.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Fall of Wickets Section */}
              {currentScorecard.fall_of_wickets && currentScorecard.fall_of_wickets.length > 0 && (
                <div className="space-y-2 pt-1">
                  <h4 className="text-xs font-black uppercase tracking-wider text-rose-400">
                    Fall of Wickets
                  </h4>
                  <div className="p-3.5 rounded-xl bg-[#081826] border border-[#1E3A5F] text-xs text-slate-300 leading-relaxed font-mono flex flex-wrap gap-2">
                    {currentScorecard.fall_of_wickets.map((fow, idx, arr) => (
                      <span key={idx} className="inline-flex items-center">
                        <span className="font-bold text-white bg-[#12263A] px-2 py-0.5 rounded border border-[#1E3A5F]">
                          {fow}
                        </span>
                        {idx < arr.length - 1 && (
                          <span className="text-slate-600 mx-1.5">•</span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="py-12 text-center text-slate-400 italic text-sm">
              Scorecard information not available yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

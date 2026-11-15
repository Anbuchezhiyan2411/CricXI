import React from "react";
import { BatterLiveInfo } from "../../types";

interface ActiveBattersCardProps {
  striker?: BatterLiveInfo | null;
  nonStriker?: BatterLiveInfo | null;
}

export const ActiveBattersCard: React.FC<ActiveBattersCardProps> = ({
  striker,
  nonStriker,
}) => {
  return (
    <div className="cricket-card p-4 sm:p-5 shadow-lg space-y-3">
      <div className="flex items-center justify-between border-b border-[#1E3A5F] pb-2.5">
        <h4 className="text-xs font-black uppercase tracking-wider text-[#C7D2E2] flex items-center space-x-1.5">
          <span>Batters at Crease</span>
        </h4>
        <span className="text-[11px] text-[#F4C430] font-black tracking-wider uppercase bg-[#F4C430]/10 px-2 py-0.5 rounded-full border border-[#F4C430]/30">
          * On Strike
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="text-slate-400 font-bold border-b border-[#1E3A5F]/70 text-[11px] uppercase tracking-wider">
              <th className="pb-2 font-black">Batter</th>
              <th className="pb-2 text-right">R</th>
              <th className="pb-2 text-right">B</th>
              <th className="pb-2 text-right">4s</th>
              <th className="pb-2 text-right">6s</th>
              <th className="pb-2 text-right">SR</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E3A5F]/50">
            {/* Striker Row */}
            {striker ? (
              <tr className="text-white bg-[#0B3D91]/20 font-semibold">
                <td className="py-3 flex items-center space-x-1.5">
                  <span className="text-[#F4C430] font-black text-sm">*</span>
                  <span className="font-black text-[#F4C430] truncate max-w-[140px] sm:max-w-[180px]">
                    {striker.player_name}
                  </span>
                  {striker.decade ? (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#081826] text-amber-400 font-mono font-medium border border-[#1E3A5F]">
                      {striker.decade}s
                    </span>
                  ) : null}
                </td>
                <td className="py-3 text-right font-black text-sm text-white font-mono">
                  {striker.runs}
                </td>
                <td className="py-3 text-right text-[#C7D2E2] font-mono">
                  {striker.balls}
                </td>
                <td className="py-3 text-right text-slate-400 font-mono">
                  {striker.fours}
                </td>
                <td className="py-3 text-right text-slate-400 font-mono">
                  {striker.sixes}
                </td>
                <td className="py-3 text-right text-emerald-400 font-black font-mono">
                  {striker.strike_rate.toFixed(1)}
                </td>
              </tr>
            ) : (
              <tr>
                <td colSpan={6} className="py-3 text-center text-slate-500 italic">
                  No batter on strike
                </td>
              </tr>
            )}

            {/* Non-Striker Row */}
            {nonStriker ? (
              <tr className="text-slate-300">
                <td className="py-3 pl-3 flex items-center space-x-1.5">
                  <span className="truncate max-w-[140px] sm:max-w-[180px] font-bold text-white">
                    {nonStriker.player_name}
                  </span>
                  {nonStriker.decade ? (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#081826] text-slate-400 font-mono font-medium border border-[#1E3A5F]">
                      {nonStriker.decade}s
                    </span>
                  ) : null}
                </td>
                <td className="py-3 text-right font-bold text-white font-mono">
                  {nonStriker.runs}
                </td>
                <td className="py-3 text-right text-slate-400 font-mono">
                  {nonStriker.balls}
                </td>
                <td className="py-3 text-right text-slate-400 font-mono">
                  {nonStriker.fours}
                </td>
                <td className="py-3 text-right text-slate-400 font-mono">
                  {nonStriker.sixes}
                </td>
                <td className="py-3 text-right text-[#C7D2E2] font-bold font-mono">
                  {nonStriker.strike_rate.toFixed(1)}
                </td>
              </tr>
            ) : (
              <tr>
                <td colSpan={6} className="py-3 text-center text-slate-500 italic">
                  No non-striker
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

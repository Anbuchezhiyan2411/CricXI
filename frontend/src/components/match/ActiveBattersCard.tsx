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
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 shadow-lg space-y-3">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
        <h4 className="text-xs font-black uppercase tracking-wider text-slate-400">
          Batters at the Crease
        </h4>
        <span className="text-[11px] text-amber-400 font-semibold">
          * on strike
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="text-slate-500 font-bold border-b border-slate-800/50">
              <th className="pb-1.5 font-bold">Batter</th>
              <th className="pb-1.5 text-right">R</th>
              <th className="pb-1.5 text-right">B</th>
              <th className="pb-1.5 text-right">4s</th>
              <th className="pb-1.5 text-right">6s</th>
              <th className="pb-1.5 text-right">SR</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/40">
            {/* Striker Row */}
            {striker ? (
              <tr className="text-white bg-amber-500/5 font-semibold">
                <td className="py-2.5 flex items-center space-x-1.5">
                  <span className="text-amber-400 font-black text-sm">*</span>
                  <span className="font-black text-amber-300 truncate max-w-[140px] sm:max-w-[180px]">
                    {striker.player_name}
                  </span>
                  {striker.decade ? (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-mono font-medium">
                      {striker.decade}s
                    </span>
                  ) : null}
                </td>
                <td className="py-2.5 text-right font-black text-sm text-white">
                  {striker.runs}
                </td>
                <td className="py-2.5 text-right text-slate-300">
                  {striker.balls}
                </td>
                <td className="py-2.5 text-right text-slate-400">
                  {striker.fours}
                </td>
                <td className="py-2.5 text-right text-slate-400">
                  {striker.sixes}
                </td>
                <td className="py-2.5 text-right text-emerald-400 font-bold">
                  {striker.strike_rate.toFixed(1)}
                </td>
              </tr>
            ) : (
              <tr>
                <td colSpan={6} className="py-2 text-center text-slate-500 italic">
                  No batter on strike
                </td>
              </tr>
            )}

            {/* Non-Striker Row */}
            {nonStriker ? (
              <tr className="text-slate-300">
                <td className="py-2.5 pl-3 flex items-center space-x-1.5">
                  <span className="truncate max-w-[140px] sm:max-w-[180px]">
                    {nonStriker.player_name}
                  </span>
                  {nonStriker.decade ? (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono font-medium">
                      {nonStriker.decade}s
                    </span>
                  ) : null}
                </td>
                <td className="py-2.5 text-right font-bold text-white">
                  {nonStriker.runs}
                </td>
                <td className="py-2.5 text-right text-slate-400">
                  {nonStriker.balls}
                </td>
                <td className="py-2.5 text-right text-slate-400">
                  {nonStriker.fours}
                </td>
                <td className="py-2.5 text-right text-slate-400">
                  {nonStriker.sixes}
                </td>
                <td className="py-2.5 text-right text-slate-300">
                  {nonStriker.strike_rate.toFixed(1)}
                </td>
              </tr>
            ) : (
              <tr>
                <td colSpan={6} className="py-2 text-center text-slate-500 italic">
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


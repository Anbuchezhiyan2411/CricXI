import React from "react";
import { BowlerLiveInfo } from "../../types";

interface ActiveBowlerCardProps {
  bowler?: BowlerLiveInfo | null;
}

export const ActiveBowlerCard: React.FC<ActiveBowlerCardProps> = ({ bowler }) => {
  return (
    <div className="cricket-card p-4 sm:p-5 shadow-lg space-y-3">
      <div className="flex items-center justify-between border-b border-[#1E3A5F] pb-2.5">
        <h4 className="text-xs font-black uppercase tracking-wider text-[#C7D2E2]">
          Current Bowler
        </h4>
        <span className="text-[11px] text-cyan-300 font-black tracking-wider uppercase bg-cyan-500/10 px-2.5 py-0.5 rounded-full border border-cyan-500/30">
          Max 4 Overs
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="text-slate-400 font-bold border-b border-[#1E3A5F]/70 text-[11px] uppercase tracking-wider">
              <th className="pb-2 font-black">Bowler</th>
              <th className="pb-2 text-right">O</th>
              <th className="pb-2 text-right">M</th>
              <th className="pb-2 text-right">R</th>
              <th className="pb-2 text-right">W</th>
              <th className="pb-2 text-right">Econ</th>
            </tr>
          </thead>
          <tbody>
            {bowler ? (
              <tr className="text-white font-semibold">
                <td className="py-3 truncate max-w-[140px] sm:max-w-[180px] flex items-center space-x-1.5">
                  <span className="font-black text-cyan-300">
                    {bowler.player_name}
                  </span>
                  {bowler.decade ? (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#081826] text-cyan-300 font-mono font-medium border border-[#1E3A5F]">
                      {bowler.decade}s
                    </span>
                  ) : null}
                </td>
                <td className="py-3 text-right font-black text-white font-mono">
                  {bowler.overs.toFixed(1)}
                </td>
                <td className="py-3 text-right text-slate-400 font-mono">
                  {bowler.maidens}
                </td>
                <td className="py-3 text-right text-slate-300 font-mono">
                  {bowler.runs_conceded}
                </td>
                <td className="py-3 text-right font-black text-sm text-[#F4C430] font-mono">
                  {bowler.wickets}
                </td>
                <td className="py-3 text-right text-cyan-400 font-black font-mono">
                  {bowler.economy.toFixed(2)}
                </td>
              </tr>
            ) : (
              <tr>
                <td colSpan={6} className="py-3 text-center text-slate-500 italic">
                  No active bowler assigned
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

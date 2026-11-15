import React from "react";
import { BowlerLiveInfo } from "../../types";

interface ActiveBowlerCardProps {
  bowler?: BowlerLiveInfo | null;
}

export const ActiveBowlerCard: React.FC<ActiveBowlerCardProps> = ({ bowler }) => {
  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 shadow-lg space-y-3">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
        <h4 className="text-xs font-black uppercase tracking-wider text-slate-400">
          Current Bowler
        </h4>
        <span className="text-[11px] text-cyan-400 font-semibold">
          Max 4 Overs
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="text-slate-500 font-bold border-b border-slate-800/50">
              <th className="pb-1.5 font-bold">Bowler</th>
              <th className="pb-1.5 text-right">O</th>
              <th className="pb-1.5 text-right">M</th>
              <th className="pb-1.5 text-right">R</th>
              <th className="pb-1.5 text-right">W</th>
              <th className="pb-1.5 text-right">Econ</th>
            </tr>
          </thead>
          <tbody>
            {bowler ? (
              <tr className="text-white font-semibold">
                <td className="py-2.5 truncate max-w-[140px] sm:max-w-[180px] flex items-center space-x-1.5">
                  <span className="font-black text-cyan-300">
                    {bowler.player_name}
                  </span>
                  {bowler.decade ? (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-300 font-mono font-medium">
                      {bowler.decade}s
                    </span>
                  ) : null}
                </td>
                <td className="py-2.5 text-right font-bold text-white">
                  {bowler.overs.toFixed(1)}
                </td>
                <td className="py-2.5 text-right text-slate-300">
                  {bowler.maidens}
                </td>
                <td className="py-2.5 text-right text-slate-300">
                  {bowler.runs_conceded}
                </td>
                <td className="py-2.5 text-right font-black text-sm text-amber-400">
                  {bowler.wickets}
                </td>
                <td className="py-2.5 text-right text-cyan-400 font-bold">
                  {bowler.economy.toFixed(2)}
                </td>
              </tr>
            ) : (
              <tr>
                <td colSpan={6} className="py-2 text-center text-slate-500 italic">
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


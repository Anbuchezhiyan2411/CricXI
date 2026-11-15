import React from "react";

interface RecentDeliveriesRibbonProps {
  recentDeliveries: string[];
}

export const RecentDeliveriesRibbon: React.FC<RecentDeliveriesRibbonProps> = ({
  recentDeliveries,
}) => {
  const getBadgeStyle = (tok: string) => {
    const t = tok.toUpperCase();
    if (t === "W") {
      return "bg-gradient-to-tr from-red-700 to-[#E53935] text-white border-red-400 font-black shadow-md shadow-red-500/30 scale-105";
    }
    if (t === "6") {
      return "bg-gradient-to-tr from-purple-800 to-indigo-600 text-[#F4C430] border-purple-400 font-black shadow-md shadow-purple-500/30 scale-105";
    }
    if (t === "4") {
      return "bg-gradient-to-tr from-amber-600 to-[#F4C430] text-[#081826] border-amber-300 font-black shadow-md shadow-[#F4C430]/30 scale-105";
    }
    if (t.includes("WD") || t.includes("NB")) {
      return "bg-amber-500/20 border-amber-500/60 text-amber-300 font-extrabold";
    }
    if (t === "•" || t === "0") {
      return "bg-[#081826] border-[#1E3A5F] text-slate-500 font-semibold";
    }
    // Singles, doubles, threes
    return "bg-[#1E3A5F]/60 border-[#1E3A5F] text-white font-bold";
  };

  return (
    <div className="cricket-card p-4 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-3">
      <div className="text-xs font-black uppercase tracking-wider text-[#C7D2E2] whitespace-nowrap flex items-center space-x-2">
        <span className="w-2 h-2 rounded-full bg-[#F4C430] animate-pulse" />
        <span>Recent Deliveries</span>
      </div>

      <div className="flex items-center space-x-2 overflow-x-auto py-1 scrollbar-none">
        {recentDeliveries.length > 0 ? (
          recentDeliveries.map((tok, idx) => (
            <div
              key={idx}
              className={`w-8 h-8 rounded-full border flex items-center justify-center text-xs transition-transform transform hover:scale-110 select-none font-mono ${getBadgeStyle(
                tok
              )}`}
            >
              {tok}
            </div>
          ))
        ) : (
          <span className="text-xs text-slate-500 italic">
            Waiting for first ball...
          </span>
        )}
      </div>
    </div>
  );
};

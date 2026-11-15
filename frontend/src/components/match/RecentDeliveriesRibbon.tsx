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
      return "bg-rose-500/20 border-rose-500/60 text-rose-400 font-black shadow-lg shadow-rose-500/10";
    }
    if (t === "6") {
      return "bg-purple-500/25 border-purple-500/60 text-purple-300 font-black shadow-lg shadow-purple-500/10";
    }
    if (t === "4") {
      return "bg-amber-500/25 border-amber-500/60 text-amber-300 font-black shadow-lg shadow-amber-500/10";
    }
    if (t.includes("WD") || t.includes("NB")) {
      return "bg-yellow-500/20 border-yellow-500/50 text-yellow-300 font-bold";
    }
    if (t === "•" || t === "0") {
      return "bg-slate-800 border-slate-700 text-slate-500 font-bold";
    }
    // Singles, doubles, threes
    return "bg-slate-800 border-slate-700 text-slate-200 font-bold";
  };

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-3">
      <div className="text-xs font-black uppercase tracking-wider text-slate-400 whitespace-nowrap">
        Recent Deliveries
      </div>

      <div className="flex items-center space-x-2 overflow-x-auto py-1">
        {recentDeliveries.length > 0 ? (
          recentDeliveries.map((tok, idx) => (
            <div
              key={idx}
              className={`w-8 h-8 rounded-full border flex items-center justify-center text-xs transition-transform transform hover:scale-110 select-none ${getBadgeStyle(
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


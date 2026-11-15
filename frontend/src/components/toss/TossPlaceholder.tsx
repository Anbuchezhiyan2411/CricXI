import React from "react";
import { CircleDot } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";

export const TossPlaceholder: React.FC = () => {
  return (
    <Card className="max-w-xl mx-auto text-center space-y-6 p-8">
      <Badge variant="highlight">Match Ceremony (Phase 2)</Badge>

      <div className="w-24 h-24 mx-auto rounded-full bg-gradient-to-tr from-amber-500 to-yellow-300 flex items-center justify-center shadow-xl shadow-amber-500/20 border-4 border-amber-200/20">
        <CircleDot className="w-12 h-12 text-slate-950 animate-pulse" />
      </div>

      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-white">The Toss</h2>
        <p className="text-sm text-slate-400 max-w-sm mx-auto">
          Both captains meet at the pitch. The toss winner decides whether to Bat or Bowl first in the simulated 20-over match.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 max-w-sm mx-auto pt-2">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 font-semibold text-sm">
          Bat First
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 font-semibold text-sm">
          Bowl First
        </div>
      </div>
    </Card>
  );
};


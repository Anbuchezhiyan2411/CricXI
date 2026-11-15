import React from "react";
import { History, Award } from "lucide-react";
import { Card } from "../components/common/Card";
import { Badge } from "../components/common/Badge";

export const MatchHistoryPage: React.FC = () => {
  return (
    <div className="space-y-6 py-6">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white flex items-center space-x-2">
            <History className="w-8 h-8 text-accent" />
            <span>Match Archives</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Historical records of simulated matches, head-to-head records, and results.
          </p>
        </div>
        <Badge variant="outline">0 Past Matches</Badge>
      </div>

      <Card className="p-12 text-center space-y-4 border-dashed border-2 border-slate-800">
        <Award className="w-12 h-12 text-slate-600 mx-auto" />
        <div className="text-lg font-semibold text-slate-300">
          No Matches Recorded Yet
        </div>
        <p className="text-sm text-slate-500 max-w-sm mx-auto">
          Completed games from Phase 2 match simulations will automatically persist into the SQLite database and be displayed here.
        </p>
      </Card>
    </div>
  );
};


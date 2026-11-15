import React from "react";
import { Award, FileText } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";

export const ScorecardPlaceholder: React.FC = () => {
  return (
    <Card className="space-y-6">
      <div className="flex flex-col sm:flex-row items-center justify-between pb-4 border-b border-slate-800 gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <FileText className="w-5 h-5 text-accent" />
            <span>Official T20 Scorecard</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Complete breakdown of batting, bowling, strike rates, economy, and extras.
          </p>
        </div>
        <Badge variant="highlight">Match Completed</Badge>
      </div>

      <div className="p-8 border-2 border-dashed border-slate-800 rounded-xl text-center space-y-3">
        <Award className="w-12 h-12 text-highlight mx-auto" />
        <div className="text-base font-semibold text-slate-200">
          Scorecard Architecture Ready (Phase 1)
        </div>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          Detailed player-by-player scorecards will calculate automatically once live simulation data is emitted in Phase 2.
        </p>
      </div>
    </Card>
  );
};


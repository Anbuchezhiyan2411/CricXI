import React from "react";
import { ScorecardPlaceholder } from "../components/scorecard/ScorecardPlaceholder";

export const ScorecardPage: React.FC = () => {
  return (
    <div className="space-y-6 py-6">
      <div className="text-center space-y-1">
        <h1 className="text-3xl font-extrabold text-white">Full Scorecard</h1>
        <p className="text-sm text-slate-400">
          Phase 1 Architecture • Comprehensive Inning Metrics & Match Summary
        </p>
      </div>

      <ScorecardPlaceholder />
    </div>
  );
};


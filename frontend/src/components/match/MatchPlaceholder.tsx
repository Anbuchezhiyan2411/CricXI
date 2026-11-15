import React from "react";
import { Radio, Activity } from "lucide-react";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";

export const MatchPlaceholder: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Live Scoreboard Header */}
      <Card className="bg-gradient-to-r from-slate-900 to-surface border-slate-700/80">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <span className="flex h-3 w-3 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
            </span>
            <span className="font-bold text-white tracking-wide uppercase text-sm">Live Match Center</span>
            <Badge variant="accent">Phase 2 Simulation Engine</Badge>
          </div>
          <div className="text-xs text-slate-400 font-mono">
            T20 Match • 20 Overs per side
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-accent uppercase tracking-wider">Team 1</span>
              <div className="text-2xl font-black text-white mt-1">165 / 4 <span className="text-sm font-normal text-slate-400">(18.2 ov)</span></div>
            </div>
            <div className="text-right text-xs text-slate-400">
              <div>CRR: 9.00</div>
              <div>Target: 178</div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Team 2</span>
              <div className="text-2xl font-black text-white mt-1">177 / 6 <span className="text-sm font-normal text-slate-400">(20.0 ov)</span></div>
            </div>
            <div className="text-right text-xs text-slate-400">
              <div>1st Innings</div>
              <div className="text-emerald-400">Completed</div>
            </div>
          </div>
        </div>
      </Card>

      {/* Simulation Engine Showcase */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 space-y-4">
          <h3 className="font-bold text-slate-200 flex items-center space-x-2">
            <Radio className="w-4 h-4 text-accent" />
            <span>Ball-by-Ball Commentary Feed</span>
          </h3>
          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800 flex items-start space-x-3">
              <span className="px-2 py-0.5 rounded bg-accent/20 text-accent font-bold">18.2</span>
              <div>
                <span className="font-bold text-white">FOUR!</span> Lofted over extra cover with textbook timing. Realistic physics-based T20 ball simulation.
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800 flex items-start space-x-3">
              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold">18.1</span>
              <div>
                Full yorker on off stump, dug out safely to mid-off for a quick single.
              </div>
            </div>
          </div>
        </Card>

        <Card className="space-y-4">
          <h3 className="font-bold text-slate-200 flex items-center space-x-2">
            <Activity className="w-4 h-4 text-highlight" />
            <span>Match Insights</span>
          </h3>
          <div className="space-y-2 text-xs text-slate-400">
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span>Required Run Rate</span>
              <span className="font-mono text-white">7.80</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span>Runs Needed</span>
              <span className="font-mono text-white">13 off 10 balls</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800">
              <span>Win Probability</span>
              <span className="font-mono text-accent">Team 1 68%</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};


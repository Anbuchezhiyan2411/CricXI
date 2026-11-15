import React from "react";
import { Play, Pause, StepForward, Gauge } from "lucide-react";

interface SimulationControlsProps {
  isPaused: boolean;
  simulationSpeed: number;
  isCompleted: boolean;
  onPlayResume: () => void;
  onPause: () => void;
  onStep: () => void;
  onSetSpeed: (speed: number) => void;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  isPaused,
  simulationSpeed,
  isCompleted,
  onPlayResume,
  onPause,
  onStep,
  onSetSpeed,
}) => {
  if (isCompleted) {
    return null;
  }

  const speedOptions = [
    { label: "0.5x", val: 0.5 },
    { label: "1.0x", val: 1.0 },
    { label: "2.0x", val: 2.0 },
    { label: "3.0x", val: 3.0 },
  ];

  return (
    <div className="cricket-card p-4 shadow-lg flex flex-wrap items-center justify-between gap-4">
      {/* Play / Pause & Step Controls */}
      <div className="flex items-center space-x-3">
        {isPaused ? (
          <button
            onClick={onPlayResume}
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#F4C430] to-amber-400 hover:from-amber-400 hover:to-amber-500 text-[#081826] font-black text-xs uppercase tracking-wider transition-all shadow-lg shadow-[#F4C430]/20 transform hover:scale-[1.03] active:scale-[0.98]"
          >
            <Play className="w-4 h-4 fill-[#081826]" />
            <span>Resume Match</span>
          </button>
        ) : (
          <button
            onClick={onPause}
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-[#081826] hover:bg-[#1E3A5F] border border-[#1E3A5F] text-[#F4C430] font-black text-xs uppercase tracking-wider transition-all shadow"
          >
            <Pause className="w-4 h-4" />
            <span>Pause Match</span>
          </button>
        )}

        {/* Step 1 Ball Button */}
        <button
          onClick={onStep}
          className="inline-flex items-center space-x-1.5 px-4 py-2.5 rounded-xl bg-[#081826] hover:bg-[#1E3A5F] border border-[#1E3A5F] text-white font-bold text-xs transition-all"
          title="Simulate 1 delivery"
        >
          <StepForward className="w-4 h-4 text-[#C7D2E2]" />
          <span>Next Ball</span>
        </button>
      </div>

      {/* Speed Controls */}
      <div className="flex items-center space-x-2">
        <div className="flex items-center space-x-1 text-[#C7D2E2] text-xs font-bold mr-1">
          <Gauge className="w-3.5 h-3.5 text-[#F4C430]" />
          <span>Speed:</span>
        </div>
        <div className="flex items-center space-x-1 bg-[#081826] p-1 rounded-xl border border-[#1E3A5F]">
          {speedOptions.map((opt) => {
            const isSelected = simulationSpeed === opt.val;
            return (
              <button
                key={opt.val}
                onClick={() => onSetSpeed(opt.val)}
                className={`px-3 py-1.5 rounded-lg text-xs font-black transition-all font-mono ${
                  isSelected
                    ? "bg-[#F4C430] text-[#081826] shadow-sm font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

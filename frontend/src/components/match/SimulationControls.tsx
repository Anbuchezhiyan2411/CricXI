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
    { label: "0.5x Slow", val: 0.5 },
    { label: "1.0x Normal", val: 1.0 },
    { label: "2.0x Fast", val: 2.0 },
    { label: "3.0x Turbo", val: 3.0 },
  ];

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 shadow-lg flex flex-wrap items-center justify-between gap-4">
      {/* Play / Pause & Step Controls */}
      <div className="flex items-center space-x-3">
        {isPaused ? (
          <button
            onClick={onPlayResume}
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs uppercase tracking-wider transition-all shadow-md transform hover:scale-[1.02] active:scale-[0.98]"
          >
            <Play className="w-4 h-4 fill-slate-950" />
            <span>Resume Match</span>
          </button>
        ) : (
          <button
            onClick={onPause}
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-amber-400 font-black text-xs uppercase tracking-wider transition-all shadow-md"
          >
            <Pause className="w-4 h-4" />
            <span>Pause Match</span>
          </button>
        )}

        {/* Step 1 Ball Button */}
        <button
          onClick={onStep}
          className="inline-flex items-center space-x-1.5 px-3.5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 font-bold text-xs transition-all"
          title="Simulate 1 delivery"
        >
          <StepForward className="w-4 h-4" />
          <span>Next Ball</span>
        </button>
      </div>

      {/* Speed Controls */}
      <div className="flex items-center space-x-2">
        <div className="flex items-center space-x-1 text-slate-500 text-xs font-bold mr-1">
          <Gauge className="w-3.5 h-3.5" />
          <span>Speed:</span>
        </div>
        <div className="flex items-center space-x-1.5 bg-slate-950/80 p-1 rounded-xl border border-slate-800">
          {speedOptions.map((opt) => (
            <button
              key={opt.val}
              onClick={() => onSetSpeed(opt.val)}
              className={`px-2.5 py-1 rounded-lg text-xs font-black transition-all ${
                simulationSpeed === opt.val
                  ? "bg-amber-500 text-slate-950 shadow"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {opt.label.split(" ")[0]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};


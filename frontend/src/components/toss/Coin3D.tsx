import React from "react";
import { Trophy, Shield, Sparkles } from "lucide-react";
import { CoinChoice } from "../../types";

interface Coin3DProps {
  isFlipping: boolean;
  result: CoinChoice | null;
  selectedCall?: CoinChoice | null;
  className?: string;
}

export const Coin3D: React.FC<Coin3DProps> = ({
  isFlipping,
  result,
  selectedCall,
  className = "",
}) => {
  // Determine rotation degree:
  // If flipping or no result yet: 0 or flip in progress
  // If result is HEADS: 1800deg (5 full rotations landing on 0)
  // If result is TAILS: 1980deg (5.5 rotations landing on 180)
  const getTransform = () => {
    if (isFlipping) {
      // Spinning through 6 rotations (2160deg)
      return "rotateY(1800deg) rotateX(20deg) scale(1.08)";
    }
    if (result === "TAILS") {
      return "rotateY(1980deg) scale(1)";
    }
    if (result === "HEADS") {
      return "rotateY(1800deg) scale(1)";
    }
    return "rotateY(0deg) scale(1)";
  };

  return (
    <div
      className={`relative flex flex-col items-center justify-center select-none ${className}`}
      style={{ perspective: 1200 }}
    >
      {/* Coin Glow / Shadow */}
      <div
        className={`absolute -bottom-6 w-36 h-8 rounded-full bg-amber-500/20 blur-xl transition-all duration-700 ${
          isFlipping ? "scale-125 opacity-80" : "scale-100 opacity-40"
        }`}
      />

      {/* 3D Coin Body */}
      <div
        className="w-40 h-40 relative rounded-full transition-all"
        style={{
          transformStyle: "preserve-3d",
          transform: getTransform(),
          transitionDuration: isFlipping ? "2600ms" : "700ms",
          transitionTimingFunction: "cubic-bezier(0.2, 0.85, 0.25, 1)",
        }}
      >
        {/* ===================== FRONT FACE (HEADS) ===================== */}
        <div
          className="absolute inset-0 rounded-full flex flex-col items-center justify-center p-3 text-amber-950 font-black shadow-2xl border-4 border-amber-300"
          style={{
            backfaceVisibility: "hidden",
            background:
              "radial-gradient(circle at 35% 30%, #fef08a 0%, #eab308 45%, #ca8a04 80%, #854d0e 100%)",
            boxShadow:
              "inset 0 0 16px rgba(254, 240, 138, 0.8), inset 0 -6px 12px rgba(113, 63, 18, 0.7), 0 10px 25px rgba(0,0,0,0.5)",
          }}
        >
          {/* Outer milled rim */}
          <div className="absolute inset-1.5 rounded-full border border-dashed border-amber-600/60 pointer-events-none" />

          {/* Heads Emblem: Cricket Trophy & Laurel */}
          <div className="relative flex flex-col items-center">
            <Trophy className="w-12 h-12 text-amber-950 drop-shadow-md stroke-[2.2]" />
            <div className="text-sm font-black tracking-widest text-amber-950 uppercase mt-1 drop-shadow-sm">
              HEADS
            </div>
            <div className="text-[9px] font-bold text-amber-900 tracking-wider uppercase opacity-85">
              CRICXI • 2026
            </div>
          </div>

          {/* Shine highlight */}
          <div className="absolute top-2 left-6 w-14 h-6 rounded-full bg-white/30 rotate-[-25deg] blur-[2px] pointer-events-none" />
        </div>

        {/* ===================== BACK FACE (TAILS) ===================== */}
        <div
          className="absolute inset-0 rounded-full flex flex-col items-center justify-center p-3 text-amber-950 font-black shadow-2xl border-4 border-amber-300"
          style={{
            backfaceVisibility: "hidden",
            transform: "rotateY(180deg)",
            background:
              "radial-gradient(circle at 35% 30%, #fef08a 0%, #eab308 45%, #ca8a04 80%, #854d0e 100%)",
            boxShadow:
              "inset 0 0 16px rgba(254, 240, 138, 0.8), inset 0 -6px 12px rgba(113, 63, 18, 0.7), 0 10px 25px rgba(0,0,0,0.5)",
          }}
        >
          {/* Outer milled rim */}
          <div className="absolute inset-1.5 rounded-full border border-dashed border-amber-600/60 pointer-events-none" />

          {/* Tails Emblem: Wickets / Shield */}
          <div className="relative flex flex-col items-center">
            <Shield className="w-12 h-12 text-amber-950 drop-shadow-md stroke-[2.2]" />
            <div className="text-sm font-black tracking-widest text-amber-950 uppercase mt-1 drop-shadow-sm">
              TAILS
            </div>
            <div className="text-[9px] font-bold text-amber-900 tracking-wider uppercase opacity-85">
              CRICXI • 2026
            </div>
          </div>

          {/* Shine highlight */}
          <div className="absolute top-2 right-6 w-14 h-6 rounded-full bg-white/30 rotate-[25deg] blur-[2px] pointer-events-none" />
        </div>
      </div>

      {/* Floating Status Label underneath */}
      <div className="mt-6 text-center h-8">
        {isFlipping ? (
          <div className="flex items-center space-x-2 text-amber-400 font-bold animate-pulse text-sm">
            <Sparkles className="w-4 h-4 animate-spin" />
            <span>Coin is in the air...</span>
          </div>
        ) : result ? (
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-black tracking-wider uppercase">
            <span>Result:</span>
            <span className="text-white bg-amber-600/80 px-2 py-0.5 rounded">
              {result}
            </span>
            {selectedCall && (
              <span className="text-slate-400 text-[11px] font-normal lowercase">
                (called {selectedCall})
              </span>
            )}
          </div>
        ) : (
          <p className="text-xs text-slate-400">
            Gold Match Coin • Traditional Flip
          </p>
        )}
      </div>
    </div>
  );
};


import React, { useState, useMemo } from "react";
import { X, ShieldAlert, Check, UserCheck } from "lucide-react";
import { Player, UserSquad } from "../../types";
import { Button } from "../common/Button";
import { Badge } from "../common/Badge";
import { cn } from "../../utils/helpers";

interface SlotSelectorModalProps {
  player: Player | null;
  mySquad: UserSquad | null;
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onConfirm: (playerId: number, battingPosition: number) => void;
}

const POSITION_LABELS: Record<number, string> = {
  1: "Opener (Pos 1)",
  2: "Opener (Pos 2)",
  3: "Top Order (Pos 3)",
  4: "Middle Order (Pos 4)",
  5: "Middle Order (Pos 5)",
  6: "All-Rounder / Finisher (Pos 6)",
  7: "Lower Middle (Pos 7)",
  8: "Lower Order (Pos 8)",
  9: "Bowler / Tail (Pos 9)",
  10: "Bowler / Tail (Pos 10)",
  11: "Bowler / Tail (Pos 11)",
};

export const SlotSelectorModal: React.FC<SlotSelectorModalProps> = ({
  player,
  mySquad,
  isOpen,
  isSubmitting,
  onClose,
  onConfirm,
}) => {
  const [selectedPosition, setSelectedPosition] = useState<number | null>(null);

  // Parse allowed positions from player
  const eligiblePositions = useMemo(() => {
    if (!player?.eligible_positions) return [];
    return player.eligible_positions
      .split(/[|,]/)
      .map((p) => parseInt(p.trim(), 10))
      .filter((p) => !isNaN(p) && p >= 1 && p <= 11);
  }, [player]);

  // Determine availability for each eligible position
  const positionSlots = useMemo(() => {
    if (!player) return [];

    return eligiblePositions.map((pos) => {
      const existingSlot = mySquad?.slots?.find((s) => s.slot_number === pos);
      const isOccupied = !!existingSlot?.is_locked || !!existingSlot?.pick;
      return {
        position: pos,
        label: POSITION_LABELS[pos] || `Position ${pos}`,
        isOccupied,
        occupantName: existingSlot?.pick?.player_name || null,
        occupantRole: existingSlot?.pick?.primary_role || null,
      };
    });
  }, [player, eligiblePositions, mySquad]);

  const hasAvailableSlot = positionSlots.some((slot) => !slot.isOccupied);

  // Reset selected position when player changes
  React.useEffect(() => {
    const firstAvailable = positionSlots.find((s) => !s.isOccupied);
    setSelectedPosition(firstAvailable ? firstAvailable.position : null);
  }, [player, positionSlots]);

  if (!isOpen || !player) return null;

  const handleConfirm = () => {
    if (selectedPosition !== null && player.player_id) {
      onConfirm(player.player_id, selectedPosition);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-surface border border-slate-800 rounded-2xl shadow-2xl p-6 overflow-hidden">
        {/* Close Button */}
        <button
          onClick={onClose}
          disabled={isSubmitting}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="space-y-1 mb-5">
          <div className="flex items-center space-x-2">
            <span className="text-xs uppercase font-extrabold tracking-wider text-accent">
              Assign Batting Position
            </span>
          </div>
          <h2 className="text-xl font-black text-white">{player.player_name}</h2>
          <div className="flex items-center space-x-2 text-xs text-slate-400">
            <Badge variant="role" roleType={player.primary_role} className="text-[10px]">
              {player.primary_role}
            </Badge>
            <span>•</span>
            <span>{player.country}</span>
            <span>•</span>
            <span>OVR: {Math.round(player.overall_rating || 0)}</span>
          </div>
        </div>

        {/* Position Selection Area */}
        <div className="space-y-3 mb-6">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Select an Open Batting Slot (1–11):
          </label>

          {!hasAvailableSlot ? (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center space-x-3">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <span>
                All eligible positions for this player ({eligiblePositions.join(", ")}) are already filled in your squad.
              </span>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-60 overflow-y-auto pr-1">
              {positionSlots.map((slot) => {
                const isSelected = selectedPosition === slot.position;
                return (
                  <button
                    key={slot.position}
                    type="button"
                    disabled={slot.isOccupied || isSubmitting}
                    onClick={() => setSelectedPosition(slot.position)}
                    className={cn(
                      "flex items-center justify-between p-3 rounded-xl border text-left transition-all duration-150",
                      slot.isOccupied
                        ? "bg-slate-900/60 border-slate-800/70 text-slate-400 cursor-not-allowed opacity-50"
                        : isSelected
                        ? "bg-accent/15 border-accent text-accent shadow-sm"
                        : "bg-slate-900/40 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-800/50"
                    )}
                  >
                    <div>
                      <div className="font-bold text-xs flex items-center space-x-1.5">
                        <span className="w-5 h-5 rounded-md bg-slate-800 flex items-center justify-center text-[11px] font-mono">
                          {slot.position}
                        </span>
                        <span className="truncate">{slot.label}</span>
                      </div>
                      {slot.isOccupied && (
                        <span className="text-[10px] text-slate-400 block mt-0.5 truncate max-w-[130px]">
                          Filled: {slot.occupantName} ({slot.occupantRole})
                        </span>
                      )}
                    </div>

                    <div>
                      {isSelected && (
                        <div className="w-5 h-5 rounded-full bg-accent flex items-center justify-center text-white">
                          <Check className="w-3.5 h-3.5 stroke-[3]" />
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={isSubmitting}
            onClick={onClose}
            className="text-xs"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            disabled={!selectedPosition || !hasAvailableSlot || isSubmitting}
            onClick={handleConfirm}
            className="text-xs font-bold px-5"
          >
            {isSubmitting ? (
              "Locking In..."
            ) : (
              <span className="flex items-center space-x-1.5">
                <UserCheck className="w-4 h-4" />
                <span>Confirm Pick</span>
              </span>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

import React, { useState, useMemo } from "react";
import { X, ShieldAlert, Check, UserCheck, Shield } from "lucide-react";
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
  6: "Finisher / AR (Pos 6)",
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#081826]/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-[#12263A] border-2 border-[#1E3A5F] rounded-2xl shadow-2xl p-6 sm:p-7 overflow-hidden text-white">
        {/* Glow accent */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#0B3D91] via-[#F4C430] to-[#138A36]" />

        {/* Close Button */}
        <button
          onClick={onClose}
          disabled={isSubmitting}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-[#1E3A5F] transition-colors"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="space-y-1.5 mb-5">
          <div className="flex items-center space-x-2">
            <span className="text-[11px] uppercase font-black tracking-widest text-[#F4C430] flex items-center space-x-1">
              <Shield className="w-3.5 h-3.5 text-[#F4C430]" />
              <span>Assign Batting Position</span>
            </span>
          </div>
          <h2 className="text-2xl font-black text-white tracking-tight">{player.player_name}</h2>
          <div className="flex items-center space-x-2.5 text-xs text-[#C7D2E2]">
            <Badge variant="role" roleType={player.primary_role} className="text-[10px] font-bold">
              {player.primary_role}
            </Badge>
            <span>•</span>
            <span className="font-medium text-slate-300">{player.country}</span>
            <span>•</span>
            <span className="font-extrabold text-[#F4C430]">OVR: {Math.round(player.overall_rating || 0)}</span>
          </div>
        </div>

        {/* Position Selection Area */}
        <div className="space-y-3 mb-6">
          <label className="text-xs font-black uppercase tracking-wider text-[#C7D2E2]">
            Select Open Batting Slot (1–11):
          </label>

          {!hasAvailableSlot ? (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center space-x-3">
              <ShieldAlert className="w-5 h-5 shrink-0 text-red-400" />
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
                        ? "bg-[#081826]/60 border-[#1E3A5F]/50 text-slate-500 cursor-not-allowed opacity-50"
                        : isSelected
                        ? "bg-[#0B3D91]/30 border-[#F4C430] text-white shadow-md shadow-[#F4C430]/10"
                        : "bg-[#081826]/70 border-[#1E3A5F] text-[#C7D2E2] hover:border-slate-500 hover:bg-[#1E3A5F]/40"
                    )}
                  >
                    <div>
                      <div className="font-bold text-xs flex items-center space-x-1.5">
                        <span
                          className={cn(
                            "w-5 h-5 rounded-md flex items-center justify-center text-[11px] font-mono font-bold",
                            isSelected
                              ? "bg-[#F4C430] text-[#081826]"
                              : "bg-[#1E3A5F] text-slate-300"
                          )}
                        >
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
                        <div className="w-5 h-5 rounded-full bg-[#F4C430] flex items-center justify-center text-[#081826]">
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
        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-[#1E3A5F]">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={isSubmitting}
            onClick={onClose}
            className="text-xs text-[#C7D2E2] hover:text-white"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="gold"
            size="sm"
            disabled={!selectedPosition || !hasAvailableSlot || isSubmitting}
            onClick={handleConfirm}
            className="text-xs font-black px-6 tracking-wide"
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

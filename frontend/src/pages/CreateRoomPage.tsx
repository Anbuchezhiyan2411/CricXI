import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, ArrowLeft, Sparkles, Trophy } from "lucide-react";
import { Button } from "../components/common/Button";
import { roomService } from "../services/roomService";
import { useGame } from "../contexts/GameContext";
import { useToast } from "../components/common/Toast";

export const CreateRoomPage: React.FC = () => {
  const navigate = useNavigate();
  const { setUser, setCurrentRoom } = useGame();
  const { addToast } = useToast();

  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = username.trim();

    if (!trimmed) {
      setError("Please enter your player name.");
      return;
    }

    if (trimmed.length < 3) {
      setError("Player name must be at least 3 characters.");
      return;
    }

    if (trimmed.length > 20) {
      setError("Player name cannot exceed 20 characters.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const room = await roomService.createRoom(trimmed);
      const hostPlayer = room.players.find((p) => p.is_host);

      if (hostPlayer) {
        setUser(hostPlayer.user_id, hostPlayer.username);
      } else if (room.current_user_id) {
        setUser(room.current_user_id, trimmed);
      }

      setCurrentRoom(room);
      addToast(`Room ${room.room_code} created successfully!`, "success");
      navigate(`/lobby?room=${room.room_code}`);
    } catch (err: any) {
      const message = err.message || "Failed to create room.";
      setError(message);
      addToast(message, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-10 px-4">
      <Link
        to="/"
        className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Home</span>
      </Link>

      <div className="cricket-card p-6 sm:p-8 space-y-6 shadow-2xl relative overflow-hidden">
        {/* Glow accent */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#0B3D91] via-[#F4C430] to-[#138A36]" />

        <div className="text-center space-y-2">
          <div className="w-16 h-16 bg-[#081826] border-2 border-[#F4C430]/60 rounded-2xl flex items-center justify-center text-[#F4C430] mx-auto shadow-xl shadow-[#F4C430]/15">
            <Trophy className="w-8 h-8 stroke-[2.2]" />
          </div>
          <h2 className="text-2xl font-black text-white tracking-tight uppercase">Create Match Room</h2>
          <p className="text-xs text-[#C7D2E2] leading-relaxed">
            Host a room, invite an opponent with a 6-character code, and draft your ultimate XI.
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center space-x-2.5 text-xs text-red-400 font-semibold">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleCreate} className="space-y-4">
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <label htmlFor="username" className="font-bold text-[#C7D2E2] uppercase tracking-wider text-[11px]">
                Your Captain Name
              </label>
              <span className="text-slate-400 font-mono text-[11px]">
                {username.trim().length}/20
              </span>
            </div>
            <input
              id="username"
              type="text"
              placeholder="e.g. MasterBlaster"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (error) setError(null);
              }}
              className="w-full px-4 py-3 bg-[#081826] border border-[#1E3A5F] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-[#F4C430] text-sm font-semibold transition-colors"
              minLength={3}
              maxLength={20}
              required
              autoFocus
            />
            <p className="text-[11px] text-slate-400">
              Between 3 and 20 characters. Will be visible to your opponent on the scoreboard.
            </p>
          </div>

          <Button
            type="submit"
            variant="gold"
            className="w-full py-3.5 text-sm font-black shadow-xl shadow-[#F4C430]/20 tracking-wider uppercase"
            isLoading={loading}
          >
            <Sparkles className="w-4 h-4 mr-2" />
            <span>Generate Room Code</span>
          </Button>
        </form>

        <div className="pt-2 border-t border-[#1E3A5F] text-center">
          <p className="text-xs text-[#C7D2E2]">
            Have a friend code already?{" "}
            <Link to="/join-room" className="text-[#F4C430] hover:underline font-bold">
              Join with Code
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

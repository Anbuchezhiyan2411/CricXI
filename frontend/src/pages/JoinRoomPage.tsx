import React, { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { KeyRound, AlertCircle, CheckCircle2, ArrowLeft, Loader2 } from "lucide-react";
import { Card } from "../components/common/Card";
import { Button } from "../components/common/Button";
import { roomService } from "../services/roomService";
import { useGame } from "../contexts/GameContext";
import { useToast } from "../components/common/Toast";
import { RoomValidateResponse } from "../types";

export const JoinRoomPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialCode = (searchParams.get("room") || "").toUpperCase();

  const { userId, setUser, setCurrentRoom } = useGame();
  const { addToast } = useToast();

  const [roomCode, setRoomCode] = useState(initialCode);
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<RoomValidateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Auto-validate room code when user types 6 characters or modifies username
  useEffect(() => {
    const cleanCode = roomCode.trim().toUpperCase();
    if (cleanCode.length === 6) {
      let isMounted = true;
      setValidating(true);
      setError(null);

      roomService
        .validateRoom(cleanCode, username || undefined, userId || undefined)
        .then((res) => {
          if (isMounted) {
            setValidationResult(res);
            if (!res.valid) {
              setError(res.message);
            }
          }
        })
        .catch(() => {
          if (isMounted) {
            setValidationResult(null);
          }
        })
        .finally(() => {
          if (isMounted) setValidating(false);
        });

      return () => {
        isMounted = false;
      };
    } else {
      setValidationResult(null);
      if (cleanCode.length > 0 && cleanCode.length < 6) {
        setError(null);
      }
    }
  }, [roomCode, username, userId]);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = roomCode.trim().toUpperCase();
    const cleanName = username.trim();

    if (!cleanCode || cleanCode.length !== 6) {
      setError("Please enter a valid 6-character room code.");
      return;
    }

    if (!cleanName || cleanName.length < 3) {
      setError("Player name must be at least 3 characters.");
      return;
    }

    if (cleanName.length > 20) {
      setError("Player name cannot exceed 20 characters.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const room = await roomService.joinRoom(cleanCode, cleanName, userId || undefined);
      const guestPlayer =
        room.players.find((p) => p.username.toLowerCase() === cleanName.toLowerCase()) ||
        room.players.find((p) => !p.is_host);

      if (guestPlayer) {
        setUser(guestPlayer.user_id, guestPlayer.username);
      } else if (room.current_user_id) {
        setUser(room.current_user_id, cleanName);
      }

      setCurrentRoom(room);
      addToast(`Joined room ${room.room_code}!`, "success");

      // Seamlessly navigate to current active game phase if resuming an in-flight match
      if (room.status === "DRAFTING") {
        navigate(`/draft?room=${room.room_code}`);
      } else if (room.status === "TOSS") {
        navigate(`/toss?room=${room.room_code}`);
      } else if (room.status === "LIVE") {
        navigate(`/live?room=${room.room_code}`);
      } else {
        navigate(`/lobby?room=${room.room_code}`);
      }
    } catch (err: any) {
      const message = err.message || "Failed to join room.";
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
        className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-400 hover:text-slate-200 mb-6 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Home</span>
      </Link>

      <Card className="space-y-6 shadow-2xl border-slate-800 bg-slate-900/90 backdrop-blur-md p-6 sm:p-8">
        <div className="text-center space-y-2">
          <div className="w-14 h-14 bg-highlight/20 border border-highlight/40 rounded-2xl flex items-center justify-center text-highlight mx-auto shadow-lg shadow-highlight/10">
            <KeyRound className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-black text-white tracking-tight">Join Room</h2>
          <p className="text-xs text-slate-400">
            Enter the 6-character room code shared by your friend to join their match lobby.
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center space-x-2.5 text-xs text-red-400">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleJoin} className="space-y-4">
          {/* Room Code Field */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <label htmlFor="roomCode" className="font-semibold text-slate-300">
                Room Code
              </label>
              {validating && (
                <span className="flex items-center space-x-1 text-slate-400 text-[11px]">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Checking...</span>
                </span>
              )}
              {validationResult?.valid && !validating && (
                <span className="flex items-center space-x-1 text-accent text-[11px] font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Room Available</span>
                </span>
              )}
            </div>
            <input
              id="roomCode"
              type="text"
              placeholder="e.g. AB4XQ2"
              value={roomCode}
              onChange={(e) => {
                setRoomCode(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""));
                if (error) setError(null);
              }}
              className="w-full px-4 py-3 bg-background border border-slate-700 rounded-xl text-white font-mono tracking-widest text-lg placeholder-slate-500 uppercase focus:outline-none focus:border-highlight text-center"
              maxLength={6}
              required
              autoFocus
            />
          </div>

          {/* Player Name Field */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <label htmlFor="username" className="font-semibold text-slate-300">
                Your Player Name
              </label>
              <span className="text-slate-500 font-mono">
                {username.trim().length}/20
              </span>
            </div>
            <input
              id="username"
              type="text"
              placeholder="e.g. YorkerKing"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (error) setError(null);
              }}
              className="w-full px-4 py-3 bg-background border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-highlight text-sm"
              minLength={3}
              maxLength={20}
              required
            />
            <p className="text-[11px] text-slate-500">
              Between 3 and 20 characters. Must be unique in this room.
            </p>
          </div>

          <Button
            type="submit"
            variant="primary"
            className="w-full py-3.5 text-sm font-bold shadow-lg shadow-highlight/20 bg-highlight hover:bg-highlight-hover text-slate-950"
            isLoading={loading}
            disabled={validating || (validationResult !== null && !validationResult.valid)}
          >
            <span>Enter Lobby</span>
          </Button>
        </form>

        <div className="pt-2 border-t border-slate-800 text-center">
          <p className="text-xs text-slate-400">
            Want to host your own match instead?{" "}
            <Link to="/create-room" className="text-highlight hover:underline font-semibold">
              Create a Room
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
};

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { LobbyCard } from "../components/lobby/LobbyCard";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { roomService } from "../services/roomService";
import { useGame } from "../contexts/GameContext";
import { useWebSocket, WebSocketEvent } from "../hooks/useWebSocket";
import { useToast } from "../components/common/Toast";

export const LobbyPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const roomCodeParam = (searchParams.get("room") || "").toUpperCase();

  const { userId, currentRoom, setCurrentRoom, clearSession } = useGame();
  const { addToast } = useToast();

  const [loading, setLoading] = useState<boolean>(!currentRoom);
  const [error, setError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState<boolean>(false);

  // Single-flight navigation guard to eliminate double/duplicate navigation
  const hasNavigatedRef = useRef<boolean>(false);
  const navTimeoutRef = useRef<number | null>(null);

  // Guaranteed single navigation to Draft
  const navigateToDraft = useCallback(
    (targetCode: string) => {
      if (hasNavigatedRef.current) return;
      hasNavigatedRef.current = true;

      if (navTimeoutRef.current) {
        clearTimeout(navTimeoutRef.current);
        navTimeoutRef.current = null;
      }

      const cleanCode = (targetCode || roomCodeParam || currentRoom?.room_code || "").trim().toUpperCase();
      if (cleanCode) {
        localStorage.setItem("cricxi_room_code", cleanCode);
        localStorage.setItem("cricxi_phase", "DRAFTING");
        navigate(`/draft?room=${cleanCode}`, { replace: true });
      } else {
        navigate("/draft", { replace: true });
      }
    },
    [navigate, roomCodeParam, currentRoom]
  );

  // Cleanup pending navigation timeouts on unmount
  useEffect(() => {
    return () => {
      if (navTimeoutRef.current) {
        clearTimeout(navTimeoutRef.current);
        navTimeoutRef.current = null;
      }
    };
  }, []);

  // Initial fetch if room is not yet loaded in context
  const fetchRoomDetails = useCallback(async () => {
    if (!roomCodeParam) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const room = await roomService.getRoom(roomCodeParam);
      if (room.status === "COMPLETED" || room.status === "ABANDONED") {
        setError("This room's match has ended.");
      } else {
        setCurrentRoom(room);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load room details.");
    } finally {
      setLoading(false);
    }
  }, [roomCodeParam, setCurrentRoom]);

  useEffect(() => {
    if (!currentRoom || currentRoom.room_code !== roomCodeParam) {
      fetchRoomDetails();
    } else {
      setLoading(false);
    }
  }, [fetchRoomDetails, currentRoom, roomCodeParam]);

  // WebSocket message callback
  const handleWebSocketMessage = useCallback(
    (event: WebSocketEvent) => {
      // If room data is attached, sync state
      if (event.room) {
        setCurrentRoom(event.room);
      }

      switch (event.type) {
        case "room_joined":
          if (event.player_id === userId) {
            addToast("Connected to match lobby.", "info");
          }
          break;

        case "player_joined":
          if (event.player_id !== userId) {
            addToast(`${event.username || "Opponent"} has joined the room!`, "success");
          }
          break;

        case "player_left":
          if (event.player_id !== userId) {
            const opponentName =
              currentRoom?.players.find((p) => p.user_id === event.player_id)?.username ||
              "Opponent";
            if (event.disconnected) {
              addToast(`${opponentName} disconnected. Waiting for reconnect...`, "warning");
            } else {
              addToast(`${opponentName} left the room.`, "warning");
            }
          }
          break;

        case "player_ready":
          if (event.player_id !== userId) {
            addToast("Opponent is Ready!", "info");
          }
          break;

        case "player_not_ready":
          if (event.player_id !== userId) {
            addToast("Opponent canceled Ready.", "info");
          }
          break;

        case "game_start": {
          if (hasNavigatedRef.current) break;
          addToast("Game is starting! Entering Draft Arena...", "success");
          const targetCode =
            event.room_code ||
            event.room?.room_code ||
            roomCodeParam ||
            currentRoom?.room_code ||
            "";
          if (navTimeoutRef.current) clearTimeout(navTimeoutRef.current);
          navTimeoutRef.current = window.setTimeout(() => {
            navigateToDraft(targetCode);
          }, 150);
          break;
        }

        case "room_updated":
        case "draft_started": {
          if (event.room?.status === "DRAFTING" && !hasNavigatedRef.current) {
            const targetCode = event.room.room_code || roomCodeParam || currentRoom?.room_code || "";
            navigateToDraft(targetCode);
          }
          break;
        }

        case "connection_error":
          addToast(event.message || "Connection error occurred.", "error");
          break;

        default:
          break;
      }
    },
    [userId, currentRoom, setCurrentRoom, addToast, navigateToDraft, roomCodeParam]
  );

  const { status, toggleReady, leaveRoom } = useWebSocket(
    roomCodeParam || currentRoom?.room_code,
    userId,
    {
      onMessage: handleWebSocketMessage,
      onError: (err) => addToast(err, "error"),
    }
  );

  const handleStartGame = async () => {
    if (!currentRoom || !userId || isStarting || hasNavigatedRef.current) return;
    setIsStarting(true);
    try {
      const updatedRoom = await roomService.startGame(currentRoom.room_code, userId);
      setCurrentRoom(updatedRoom);
      addToast("Starting match draft...", "success");

      // WebSocket game_start handles immediate navigation for both Host and Guest.
      // As a reliable fallback, if game_start didn't navigate within 1200ms, execute navigation.
      if (!hasNavigatedRef.current) {
        if (navTimeoutRef.current) clearTimeout(navTimeoutRef.current);
        navTimeoutRef.current = window.setTimeout(() => {
          navigateToDraft(updatedRoom.room_code);
        }, 1200);
      }
    } catch (err: any) {
      addToast(err.message || "Failed to start game.", "error");
      setIsStarting(false);
    }
  };

  const handleLeaveRoom = async () => {
    if (!currentRoom || !userId) return;
    try {
      leaveRoom();
      await roomService.leaveRoom(currentRoom.room_code, userId);
      clearSession();
      addToast("You left the lobby.", "info");
      navigate("/");
    } catch (err: any) {
      clearSession();
      navigate("/");
    }
  };

  if (loading) {
    return <LoadingSpinner label="Entering match lobby..." />;
  }

  if (error || !currentRoom) {
    return (
      <div className="max-w-md mx-auto text-center py-16 px-4">
        <div className="p-8 rounded-2xl bg-surface border border-slate-800 space-y-4 shadow-xl">
          <h3 className="text-xl font-bold text-white">Match Lobby</h3>
          <p className="text-sm text-slate-400">
            {error || "Ready for a match? Create a new room or join your friend."}
          </p>
          <div className="pt-2 flex justify-center space-x-3">
            <button
              onClick={() => navigate("/create-room")}
              className="px-4 py-2 text-xs font-bold rounded-lg bg-accent text-white"
            >
              Create Room
            </button>
            <button
              onClick={() => navigate("/join-room")}
              className="px-4 py-2 text-xs font-bold rounded-lg bg-surface border border-slate-700 text-slate-300"
            >
              Join Room
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 py-8 px-4 max-w-5xl mx-auto relative">
      <div className="text-center space-y-2">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#12263A] border border-[#1E3A5F] text-[#F4C430] text-xs font-black uppercase tracking-widest shadow-md">
          <span>Official Match Pre-Game</span>
        </div>
        <h1 className="text-3xl sm:text-5xl font-black text-white tracking-tight font-display drop-shadow-md">
          T20 Match Lobby
        </h1>
        <p className="text-xs sm:text-sm text-[#C7D2E2] max-w-md mx-auto font-medium">
          Multiplayer squad room • Both captains confirm ready to initiate the strategic draft
        </p>
      </div>

      <LobbyCard
        room={currentRoom}
        currentUserId={userId}
        connectionStatus={status}
        isStarting={isStarting}
        onReadyToggle={toggleReady}
        onStartGame={handleStartGame}
        onLeaveRoom={handleLeaveRoom}
      />
    </div>
  );
};

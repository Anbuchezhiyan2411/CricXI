import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useGame } from "../contexts/GameContext";
import { useWebSocket, WebSocketEvent } from "../hooks/useWebSocket";
import { useToast } from "../components/common/Toast";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { MatchHeader } from "../components/match/MatchHeader";
import { ScoreboardHero } from "../components/match/ScoreboardHero";
import { ActiveBattersCard } from "../components/match/ActiveBattersCard";
import { ActiveBowlerCard } from "../components/match/ActiveBowlerCard";
import { RecentDeliveriesRibbon } from "../components/match/RecentDeliveriesRibbon";
import { LiveCommentaryFeed } from "../components/match/LiveCommentaryFeed";
import { SimulationControls } from "../components/match/SimulationControls";
import { ScorecardModal } from "../components/match/ScorecardModal";
import { MatchCelebrationCard } from "../components/match/MatchCelebrationCard";
import { matchService } from "../services/matchService";
import { roomService } from "../services/roomService";
import { LiveMatchStateResponse } from "../types";
import { AlertCircle, Trophy } from "lucide-react";

export const LiveMatchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const { userId, username, currentRoom, setUser, setCurrentRoom } = useGame();

  // Resolve active room code from URL params, context, or localStorage
  const roomCode = useMemo(() => {
    const fromQuery = searchParams.get("room");
    if (fromQuery) return fromQuery.toUpperCase().trim();
    if (currentRoom?.room_code) return currentRoom.room_code.toUpperCase().trim();
    const fromStorage = localStorage.getItem("cricxi_room_code");
    return fromStorage ? fromStorage.toUpperCase().trim() : "";
  }, [searchParams, currentRoom]);

  // Persist room code for reload resilience
  useEffect(() => {
    if (roomCode) {
      localStorage.setItem("cricxi_room_code", roomCode);
    }
  }, [roomCode]);

  // Active user ID
  const activeUserId = userId || localStorage.getItem("cricxi_user_id") || "";

  // Stable refs for background hydration to avoid recreating callbacks
  const activeUserIdRef = useRef<string>(activeUserId);
  activeUserIdRef.current = activeUserId;
  const usernameRef = useRef<string | null>(username);
  usernameRef.current = username;
  const setUserRef = useRef(setUser);
  setUserRef.current = setUser;
  const setCurrentRoomRef = useRef(setCurrentRoom);
  setCurrentRoomRef.current = setCurrentRoom;

  // Component State
  const [matchState, setMatchState] = useState<LiveMatchStateResponse | null>(null);
  const matchStateRef = useRef<LiveMatchStateResponse | null>(null);
  matchStateRef.current = matchState;

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isScorecardOpen, setIsScorecardOpen] = useState<boolean>(false);
  const [isStartingRematch, setIsStartingRematch] = useState<boolean>(false);
  const [isWaitingForRematch, setIsWaitingForRematch] = useState<boolean>(false);
  const [opponentWantsRematch, setOpponentWantsRematch] = useState<boolean>(false);

  // Disconnect recovery state
  const [isOpponentDisconnected, setIsOpponentDisconnected] = useState<boolean>(false);
  const [disconnectCountdown, setDisconnectCountdown] = useState<number | null>(null);
  const [abandonmentNotice, setAbandonmentNotice] = useState<{
    title: string;
    message: string;
    submessage: string;
  } | null>(null);

  // Clean wipe state ONLY when room code genuinely changes (e.g. Rematch)
  const prevRoomCodeRef = useRef<string | null>(null);
  useEffect(() => {
    if (prevRoomCodeRef.current && prevRoomCodeRef.current !== roomCode) {
      setMatchState(null);
      matchStateRef.current = null;
      setIsScorecardOpen(false);
      setIsStartingRematch(false);
      setIsWaitingForRematch(false);
      setOpponentWantsRematch(false);
      setError(null);
    }
    prevRoomCodeRef.current = roomCode;
  }, [roomCode]);

  // Sync Match State from Backend
  const syncMatchState = useCallback(
    async (isInitial = false) => {
      if (!roomCode) {
        setError("No room code found. Please join or create a room.");
        setLoading(false);
        return;
      }

      try {
        if (isInitial && !matchStateRef.current) {
          setLoading(true);
        }

        // Re-hydrate user identity if needed and check if match was abandoned
        try {
          const room = await roomService.getRoom(roomCode);
          if (room.status === "ABANDONED") {
            localStorage.removeItem("cricxi_room_code");
            localStorage.removeItem("cricxi_phase");
            addToast("This match has ended. Returning to lobby.", "info");
            navigate("/lobby", { replace: true });
            return;
          }
          setCurrentRoomRef.current(room);
          const currentActiveId = activeUserIdRef.current;
          if (!currentActiveId) {
            const savedUsername = localStorage.getItem("cricxi_username") || usernameRef.current;
            if (savedUsername) {
              const matched = room.players.find(
                (p) => p.username.toLowerCase() === savedUsername.toLowerCase()
              );
              if (matched && matched.user_id !== currentActiveId) {
                setUserRef.current(matched.user_id, matched.username);
              }
            }
          }
        } catch {
          // ignore room fetch error
        }

        // Idempotent read-only fetch of live match state, falling back to init only if not initialized
        let state: LiveMatchStateResponse;
        try {
          state = await matchService.getMatchState(roomCode);
        } catch {
          state = await matchService.initMatch(roomCode, true);
        }
        matchStateRef.current = state;
        setMatchState(state);
        setError(null);
      } catch (err: any) {
        console.error("Error loading live match:", err);
        setError(err.message || "Failed to load live match simulation.");
      } finally {
        setLoading(false);
      }
    },
    [roomCode, navigate, addToast]
  );

  // Initial fetch on mount - guarded to run exactly once per room code
  const hasFetchedMatchRef = useRef<string | null>(null);
  useEffect(() => {
    if (roomCode && hasFetchedMatchRef.current !== roomCode) {
      hasFetchedMatchRef.current = roomCode;
      syncMatchState(true);
    }
  }, [roomCode, syncMatchState]);

  // Handle WebSocket Event Updates
  const handleWebSocketMessage = useCallback(
    (event: WebSocketEvent) => {
      if (!event || !event.type) return;

      const currentActiveId = activeUserIdRef.current;

      if (event.type === "rematch_status") {
        const readyIds: string[] = event.ready_user_ids || [];
        if (currentActiveId && readyIds.includes(currentActiveId)) {
          setIsWaitingForRematch(true);
        } else if (readyIds.length > 0) {
          setOpponentWantsRematch(true);
          addToast("Opponent requested a rematch! Click Play Another Match to accept.", "info");
        }
        return;
      }

      if (
        event.type === "room_reset" ||
        event.type === "new_match_ready" ||
        event.type === "play_again"
      ) {
        const targetRoomCode = event.room_code || event.new_room_code || roomCode;
        if (targetRoomCode) {
          localStorage.setItem("cricxi_room_code", targetRoomCode);
          setIsScorecardOpen(false);
          addToast("Both players confirmed! Starting fresh match draft...", "success");
          navigate(`/draft?room=${targetRoomCode}`, { replace: true });
        }
        return;
      }

      if (
        (event.type === "match_state_updated" ||
          event.type === "match_initialized" ||
          event.type === "match_started" ||
          event.type === "match_completed" ||
          event.type === "match_control_updated") &&
        event.match_state
      ) {
        const fresh = event.match_state as LiveMatchStateResponse;
        matchStateRef.current = fresh;
        setMatchState(fresh);
      } else if (event.type === "ball_result" && event.match_state) {
        const fresh = event.match_state as LiveMatchStateResponse;
        matchStateRef.current = fresh;
        setMatchState(fresh);
      } else if (event.type === "player_disconnected") {
        if (event.user_id && event.user_id === currentActiveId) return;
        setIsOpponentDisconnected(true);
        setDisconnectCountdown(typeof event.seconds_remaining === "number" ? event.seconds_remaining : 30);
        addToast("Opponent disconnected. Match simulation paused.", "warning");
      } else if (event.type === "disconnect_countdown_tick") {
        if (event.user_id && event.user_id === currentActiveId) return;
        setIsOpponentDisconnected(true);
        if (typeof event.seconds_remaining === "number") {
          setDisconnectCountdown(event.seconds_remaining);
        }
      } else if (event.type === "player_reconnected") {
        setIsOpponentDisconnected(false);
        setDisconnectCountdown(null);
        addToast("Opponent reconnected! Resuming match simulation...", "success");
      } else if (event.type === "disconnect_timeout") {
        setIsOpponentDisconnected(false);
        setDisconnectCountdown(null);
        localStorage.removeItem("cricxi_room_code");
        localStorage.removeItem("cricxi_phase");
        setAbandonmentNotice({
          title: "Opponent Disconnected",
          message: "Match abandoned. You win by opponent disconnect.",
          submessage: "Returning to lobby...",
        });
        setTimeout(() => {
          navigate("/lobby", { replace: true });
        }, 2500);
      } else if (event.type === "match_abandoned") {
        setIsOpponentDisconnected(false);
        setDisconnectCountdown(null);
        localStorage.removeItem("cricxi_room_code");
        localStorage.removeItem("cricxi_phase");
        navigate("/lobby", { replace: true });
      } else if (event.type === "player_left") {
        if (event.user_id && event.user_id === currentActiveId) return;
        setIsOpponentDisconnected(false);
        setDisconnectCountdown(null);
        localStorage.removeItem("cricxi_room_code");
        localStorage.removeItem("cricxi_phase");
        setAbandonmentNotice({
          title: "Opponent Left",
          message: event.message || "Opponent has left the game. Match abandoned.",
          submessage: "Returning to lobby...",
        });
        setTimeout(() => {
          navigate("/lobby", { replace: true });
        }, 2500);
      }
    },
    [navigate, roomCode, addToast]
  );

  // Rematch / Play Another Match Handler (Multiplayer Synchronization Barrier)
  const handlePlayAgain = async () => {
    const currentActiveId = activeUserIdRef.current;
    if (!roomCode || !currentActiveId) return;
    try {
      setIsStartingRematch(true);
      const res = await roomService.playAgain(roomCode, currentActiveId);
      if (res.is_barrier_met) {
        const targetCode = res.new_room_code || res.old_room_code || roomCode;
        localStorage.setItem("cricxi_room_code", targetCode);
        addToast("Both players confirmed! Transitioning to Draft...", "success");
        navigate(`/draft?room=${targetCode}`, { replace: true });
      } else {
        setIsWaitingForRematch(true);
        addToast("Rematch requested! Waiting for opponent to confirm...", "info");
      }
    } catch (err: any) {
      console.error("Error starting rematch:", err);
      addToast(err.message || "Failed to start rematch.", "error");
    } finally {
      setIsStartingRematch(false);
    }
  };

  // WebSocket Connection
  const isReadyForSocket = !!roomCode && !!activeUserId;
  const { sendMessage } = useWebSocket(
    isReadyForSocket ? roomCode : null,
    isReadyForSocket ? activeUserId : null,
    {
      enabled: isReadyForSocket,
      onMessage: handleWebSocketMessage,
    }
  );

  // Play / Resume Simulation
  const handlePlayResume = async () => {
    if (!roomCode) return;
    try {
      const updated = await matchService.controlSimulation(roomCode, { action: "play" });
      matchStateRef.current = updated;
      setMatchState(updated);
      sendMessage({ type: "match_control", control_action: "play" });
      addToast("Match simulation resumed.", "info");
    } catch (err: any) {
      addToast(err.message || "Failed to resume match.", "error");
    }
  };

  // Pause Simulation
  const handlePause = async () => {
    if (!roomCode) return;
    try {
      const updated = await matchService.controlSimulation(roomCode, { action: "pause" });
      matchStateRef.current = updated;
      setMatchState(updated);
      sendMessage({ type: "match_control", control_action: "pause" });
      addToast("Match simulation paused.", "info");
    } catch (err: any) {
      addToast(err.message || "Failed to pause match.", "error");
    }
  };

  // Step 1 Delivery
  const handleStep = async () => {
    if (!roomCode) return;
    try {
      const updated = await matchService.stepDelivery(roomCode);
      matchStateRef.current = updated;
      setMatchState(updated);
      sendMessage({ type: "request_match_state" });
    } catch (err: any) {
      addToast(err.message || "Failed to step delivery.", "error");
    }
  };

  // Set Speed
  const handleSetSpeed = async (speed: number) => {
    if (!roomCode) return;
    try {
      const updated = await matchService.controlSimulation(roomCode, {
        action: "set_speed",
        speed,
      });
      matchStateRef.current = updated;
      setMatchState(updated);
      sendMessage({ type: "match_control", control_action: "set_speed", speed });
      addToast(`Simulation speed set to ${speed}x.`, "info");
    } catch (err: any) {
      addToast(err.message || "Failed to set speed.", "error");
    }
  };

  // Loading State
  if (loading || !matchState) {
    return <LoadingSpinner label="Entering Cricket Arena..." />;
  }

  // Error State
  if (error) {
    return (
      <div className="max-w-md mx-auto text-center py-16 px-4">
        <div className="p-8 rounded-2xl bg-slate-900 border border-slate-800 space-y-4 shadow-xl">
          <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
          <h3 className="text-xl font-bold text-white">Match Arena Unavailable</h3>
          <p className="text-sm text-slate-400">{error}</p>
          <div className="pt-2 flex justify-center space-x-3">
            <button
              onClick={() => syncMatchState(true)}
              className="px-4 py-2 text-xs font-bold rounded-lg bg-amber-500 text-slate-950 hover:bg-amber-400"
            >
              Retry
            </button>
            <button
              onClick={() => navigate(`/toss?room=${roomCode}`)}
              className="px-4 py-2 text-xs font-bold rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700"
            >
              Return to Toss
            </button>
          </div>
        </div>
      </div>
    );
  }

  const isCompleted = matchState.status === "COMPLETED" || matchState.status === "TIED";

  return (
    <div className="py-6 px-3 sm:px-6 max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
      {/* Disconnect Abandonment Modal */}
      {abandonmentNotice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <div className="max-w-md w-full p-6 sm:p-8 rounded-2xl bg-slate-900 border border-amber-500/50 shadow-2xl text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-amber-500/20 text-amber-400 mx-auto flex items-center justify-center border border-amber-500/40">
              <Trophy className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-black text-white">{abandonmentNotice.title}</h2>
            <p className="text-sm font-semibold text-amber-300">{abandonmentNotice.message}</p>
            <div className="flex items-center justify-center space-x-2 text-xs text-slate-400 pt-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>{abandonmentNotice.submessage}</span>
            </div>
          </div>
        </div>
      )}

      {/* Opponent Disconnected Banner */}
      {isOpponentDisconnected && disconnectCountdown !== null && (
        <div className="p-4 rounded-xl bg-amber-500/15 border border-amber-500/40 text-amber-200 flex items-center justify-between shadow-lg backdrop-blur-sm animate-pulse">
          <div className="flex items-center space-x-3">
            <span className="w-3 h-3 rounded-full bg-amber-400 animate-ping" />
            <div>
              <p className="font-bold text-sm">Opponent Disconnected</p>
              <p className="text-xs text-amber-300/80">Match simulation is paused at exact delivery. Waiting for opponent to reconnect...</p>
            </div>
          </div>
          <div className="text-right">
            <span className="font-mono text-2xl font-black text-amber-400">{disconnectCountdown}s</span>
          </div>
        </div>
      )}

      {/* 1. Header with Teams, Room Code, Status */}
      <MatchHeader
        matchState={matchState}
        onOpenScorecard={() => setIsScorecardOpen(true)}
      />

      {/* 2. Completed Celebration Banner (if match finished) */}
      {isCompleted && (
        <MatchCelebrationCard
          matchState={matchState}
          onOpenScorecard={() => setIsScorecardOpen(true)}
          onReturnToLobby={() => navigate("/lobby" + (roomCode ? `?room=${roomCode}` : ""))}
          onPlayAgain={handlePlayAgain}
          isStartingRematch={isStartingRematch}
          isWaitingForRematch={isWaitingForRematch}
          opponentWantsRematch={opponentWantsRematch}
        />
      )}

      {/* 3. Hero Scoreboard (Runs/Wickets, Overs, CRR, Chase Target/RRR) */}
      <ScoreboardHero matchState={matchState} />

      {/* 4. Recent Deliveries Ribbon (Last 6-12 balls) */}
      <RecentDeliveriesRibbon recentDeliveries={matchState.recent_deliveries} />

      {/* 5. Main Arena Grid: Active Players & Live Commentary */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (5 cols): Active Batters & Current Bowler */}
        <div className="lg:col-span-5 space-y-4">
          <ActiveBattersCard
            striker={matchState.striker}
            nonStriker={matchState.non_striker}
          />
          <ActiveBowlerCard bowler={matchState.current_bowler} />
        </div>

        {/* Right Column (7 cols): Live Commentary Feed */}
        <div className="lg:col-span-7">
          <LiveCommentaryFeed commentary={matchState.commentary} />
        </div>
      </div>

      {/* 6. Simulation Controls (Play, Pause, Step, Speeds) */}
      <SimulationControls
        isPaused={matchState.is_paused}
        simulationSpeed={matchState.simulation_speed}
        isCompleted={isCompleted}
        onPlayResume={handlePlayResume}
        onPause={handlePause}
        onStep={handleStep}
        onSetSpeed={handleSetSpeed}
      />

      {/* 7. Full Official Scorecard Modal */}
      <ScorecardModal
        isOpen={isScorecardOpen}
        onClose={() => setIsScorecardOpen(false)}
        inn1={matchState.first_innings_scorecard}
        inn2={matchState.second_innings_scorecard}
      />
    </div>
  );
};

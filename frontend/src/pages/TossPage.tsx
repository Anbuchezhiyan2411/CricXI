import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
  Trophy,
  Shield,
  CircleDot,
  AlertCircle,
  Clock,
  CheckCircle2,
} from "lucide-react";
import { useGame } from "../contexts/GameContext";
import { useWebSocket, WebSocketEvent } from "../hooks/useWebSocket";
import { useToast } from "../components/common/Toast";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { Coin3D } from "../components/toss/Coin3D";
import { TossCeremony } from "../components/toss/TossCeremony";
import { tossService } from "../services/tossService";
import { roomService } from "../services/roomService";
import { CoinChoice, PitchDecision, TossStateResponse, Room } from "../types";

export const TossPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const { userId, username, currentRoom, setUser, setCurrentRoom } = useGame();

  // Resolve room code from URL params, context, or localStorage
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

  // Active user ID from context or localStorage
  const activeUserId = userId || localStorage.getItem("cricxi_user_id") || "";

  // Stable refs for background hydration to avoid recreating callbacks
  const activeUserIdRef = useRef<string>(activeUserId);
  activeUserIdRef.current = activeUserId;
  const usernameRef = useRef<string | null>(username);
  usernameRef.current = username;
  const setUserRef = useRef(setUser);
  setUserRef.current = setUser;
  const currentRoomRef = useRef<Room | null>(currentRoom);
  currentRoomRef.current = currentRoom;
  const setCurrentRoomRef = useRef(setCurrentRoom);
  setCurrentRoomRef.current = setCurrentRoom;

  // Component State
  const [tossState, setTossState] = useState<TossStateResponse | null>(null);
  const tossStateRef = useRef<TossStateResponse | null>(null);
  tossStateRef.current = tossState;

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isFlipping, setIsFlipping] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Disconnect recovery state
  const [isOpponentDisconnected, setIsOpponentDisconnected] = useState<boolean>(false);
  const [disconnectCountdown, setDisconnectCountdown] = useState<number | null>(null);
  const [abandonmentNotice, setAbandonmentNotice] = useState<{
    title: string;
    message: string;
    submessage: string;
  } | null>(null);

  // Single-flight navigation guard to Live Match
  const hasNavigatedToLiveRef = useRef<boolean>(false);
  const liveNavTimeoutRef = useRef<number | null>(null);

  const navigateToLiveMatch = useCallback(
    (targetMatchId?: string) => {
      if (hasNavigatedToLiveRef.current) return;
      hasNavigatedToLiveRef.current = true;

      if (liveNavTimeoutRef.current) {
        clearTimeout(liveNavTimeoutRef.current);
        liveNavTimeoutRef.current = null;
      }

      const matchId = targetMatchId || tossStateRef.current?.match_id || "";
      const cleanCode = (roomCode || "").trim().toUpperCase();
      localStorage.setItem("cricxi_room_code", cleanCode);
      localStorage.setItem("cricxi_phase", "LIVE");
      navigate(`/live?room=${cleanCode}${matchId ? `&match=${matchId}` : ""}`, { replace: true });
    },
    [navigate, roomCode]
  );

  // Cleanup pending live navigation timeouts on unmount
  useEffect(() => {
    return () => {
      if (liveNavTimeoutRef.current) {
        clearTimeout(liveNavTimeoutRef.current);
        liveNavTimeoutRef.current = null;
      }
    };
  }, []);

  // Flip animation timer reference
  const flipTimerRef = useRef<number | null>(null);

  // Cleanup flip timer on unmount
  useEffect(() => {
    return () => {
      if (flipTimerRef.current) {
        clearTimeout(flipTimerRef.current);
      }
    };
  }, []);

  // Clean wipe state ONLY when room code genuinely changes (e.g. Rematch)
  const prevRoomCodeRef = useRef<string | null>(null);
  useEffect(() => {
    if (prevRoomCodeRef.current && prevRoomCodeRef.current !== roomCode) {
      setTossState(null);
      tossStateRef.current = null;
      setIsFlipping(false);
      setIsSubmitting(false);
      setError(null);
    }
    prevRoomCodeRef.current = roomCode;
  }, [roomCode]);

  // Fetch / Initialize Toss Session
  const syncTossState = useCallback(async (isInitial = false) => {
    if (!roomCode) {
      setError("No room code found. Please join or create a room.");
      setLoading(false);
      return;
    }

    try {
      if (isInitial && !tossStateRef.current) {
        setLoading(true);
      }

      // Check if room has completed/abandoned
      try {
        const room = await roomService.getRoom(roomCode);
        if (room.status === "COMPLETED" || room.status === "ABANDONED") {
          localStorage.removeItem("cricxi_room_code");
          localStorage.removeItem("cricxi_phase");
          addToast("This match has already ended. Returning to lobby.", "info");
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
        // ignore error
      }

      // Initialize or fetch toss state
      const state = await tossService.initToss(roomCode, activeUserIdRef.current || undefined);
      tossStateRef.current = state;
      setTossState(state);
      setError(null);
    } catch (err: any) {
      console.error("Error initializing toss state:", err);
      setError(err.message || "Failed to load toss ceremony.");
    } finally {
      setLoading(false);
    }
  }, [roomCode, navigate, addToast]);

  // Initial fetch on mount - guarded to run exactly once per room code
  const hasFetchedTossRef = useRef<string | null>(null);
  useEffect(() => {
    if (roomCode && hasFetchedTossRef.current !== roomCode) {
      hasFetchedTossRef.current = roomCode;
      syncTossState(true);
    }
  }, [roomCode, syncTossState]);

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = useCallback(
    (event: WebSocketEvent) => {
      if (!event || !event.type) return;

      if (
        event.type === "room_reset" ||
        event.type === "new_match_ready" ||
        event.type === "play_again"
      ) {
        const target = event.new_room_code || event.room_code || roomCode;
        localStorage.setItem("cricxi_room_code", target);
        navigate(`/draft?room=${target}`);
        return;
      }

      if (event.type === "toss_state_updated" && event.toss_state) {
        const freshState = event.toss_state as TossStateResponse;
        const currentId = activeUserIdRef.current;
        if (currentId) {
          freshState.is_current_user_caller = currentId === freshState.caller_id;
          freshState.is_current_user_winner = currentId === freshState.winner_id;
        }
        tossStateRef.current = freshState;
        setTossState(freshState);
      } else if (event.type === "toss_flipped") {
        // Trigger 2.6s flip animation
        setIsFlipping(true);
        if (flipTimerRef.current) {
          clearTimeout(flipTimerRef.current);
        }
        flipTimerRef.current = window.setTimeout(() => {
          setIsFlipping(false);
          if (event.toss_state) {
            const fresh = event.toss_state as TossStateResponse;
            const currentId = activeUserIdRef.current;
            if (currentId) {
              fresh.is_current_user_caller = currentId === fresh.caller_id;
              fresh.is_current_user_winner = currentId === fresh.winner_id;
            }
            tossStateRef.current = fresh;
            setTossState(fresh);
          }
        }, 2600);
      } else if (
        (event.type === "toss_completed" || event.type === "match_started") &&
        (event.toss_state || event.match_state)
      ) {
        if (event.toss_state) {
          const freshState = event.toss_state as TossStateResponse;
          const currentId = activeUserIdRef.current;
          if (currentId) {
            freshState.is_current_user_caller = currentId === freshState.caller_id;
            freshState.is_current_user_winner = currentId === freshState.winner_id;
          }
          tossStateRef.current = freshState;
          setTossState(freshState);
        }

        const room = currentRoomRef.current;
        if (room) {
          setCurrentRoomRef.current({
            ...room,
            status: "LIVE",
          });
        }

        const matchId = event.match_id || tossStateRef.current?.match_id || "";
        if (!hasNavigatedToLiveRef.current) {
          addToast("Toss decided! Proceeding to Live Match...", "info");
          if (liveNavTimeoutRef.current) clearTimeout(liveNavTimeoutRef.current);
          liveNavTimeoutRef.current = window.setTimeout(() => {
            navigateToLiveMatch(matchId);
          }, 1000);
        }
      } else if (event.type === "player_disconnected") {
        if (event.user_id && event.user_id === activeUserIdRef.current) return;
        setIsOpponentDisconnected(true);
        setDisconnectCountdown(typeof event.seconds_remaining === "number" ? event.seconds_remaining : 30);
        addToast("Opponent disconnected. Waiting for reconnect...", "warning");
      } else if (event.type === "disconnect_countdown_tick") {
        if (event.user_id && event.user_id === activeUserIdRef.current) return;
        setIsOpponentDisconnected(true);
        if (typeof event.seconds_remaining === "number") {
          setDisconnectCountdown(event.seconds_remaining);
        }
      } else if (event.type === "player_reconnected") {
        setIsOpponentDisconnected(false);
        setDisconnectCountdown(null);
        addToast("Opponent reconnected! Resuming toss...", "success");
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
        if (event.user_id && event.user_id === activeUserIdRef.current) return;
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
    [navigate, roomCode, addToast, navigateToLiveMatch]
  );

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

  // Handle Calling Heads or Tails
  const handleCall = async (choice: CoinChoice) => {
    if (!roomCode || !activeUserId || isSubmitting || isFlipping) return;

    try {
      setIsSubmitting(true);
      setIsFlipping(true);

      // Submit via REST API (which triggers WS broadcast to both players)
      const updatedState = await tossService.makeCall(roomCode, {
        user_id: activeUserId,
        choice,
      });

      // Also notify WebSocket channel
      sendMessage({
        type: "toss_call",
        choice,
      });

      // Finish flip animation smoothly
      if (flipTimerRef.current) {
        clearTimeout(flipTimerRef.current);
      }
      flipTimerRef.current = window.setTimeout(() => {
        setIsFlipping(false);
        if (activeUserId) {
          updatedState.is_current_user_caller = activeUserId === updatedState.caller_id;
          updatedState.is_current_user_winner = activeUserId === updatedState.winner_id;
        }
        tossStateRef.current = updatedState;
        setTossState(updatedState);
      }, 2600);
    } catch (err: any) {
      setIsFlipping(false);
      addToast(err.message || "Failed to make toss call.", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Bat or Bowl Decision (sends exactly ONE request)
  const handleDecision = async (decision: PitchDecision) => {
    if (!roomCode || !activeUserId || isSubmitting) return;

    try {
      setIsSubmitting(true);
      const updatedState = await tossService.makeDecision(roomCode, {
        user_id: activeUserId,
        decision,
      });

      if (activeUserId) {
        updatedState.is_current_user_caller = activeUserId === updatedState.caller_id;
        updatedState.is_current_user_winner = activeUserId === updatedState.winner_id;
      }
      tossStateRef.current = updatedState;
      setTossState(updatedState);
      addToast(`Toss Decision: Elected to ${decision} first! Match starting...`, "success");
    } catch (err: any) {
      addToast(err.message || "Failed to submit toss decision.", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Transition to Live Match
  const handleProceedToMatch = useCallback(() => {
    navigateToLiveMatch();
  }, [navigateToLiveMatch]);

  // Loading State
  if (loading || !tossState) {
    return <LoadingSpinner label="Setting up Toss Ceremony..." />;
  }

  // Error State
  if (error) {
    return (
      <div className="max-w-md mx-auto text-center py-16 px-4">
        <div className="cricket-card p-8 space-y-4 shadow-xl">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />
          <h3 className="text-xl font-black text-white">Toss Ceremony Error</h3>
          <p className="text-sm text-[#C7D2E2]">{error}</p>
          <div className="pt-2 flex justify-center space-x-3">
            <button
              onClick={() => syncTossState(true)}
              className="px-5 py-2.5 text-xs font-black rounded-xl bg-gradient-to-r from-[#F4C430] to-amber-500 text-[#081826] hover:scale-[1.02] transition-transform"
            >
              Retry
            </button>
            <button
              onClick={() => navigate(`/draft?room=${roomCode}`)}
              className="px-5 py-2.5 text-xs font-bold rounded-xl bg-[#081826] border border-[#1E3A5F] text-[#C7D2E2] hover:text-white"
            >
              Return to Draft
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Draft Incomplete Guard
  if (!tossState.draft_completed) {
    return (
      <div className="max-w-lg mx-auto text-center py-16 px-4">
        <div className="cricket-card p-8 space-y-5 shadow-2xl">
          <Clock className="w-12 h-12 text-[#F4C430] mx-auto animate-pulse" />
          <h2 className="text-2xl font-black text-white uppercase tracking-wide">
            Draft In Progress
          </h2>
          <p className="text-sm text-[#C7D2E2] leading-relaxed">
            {tossState.message ||
              "Both players must draft exactly 11 players before the coin toss ceremony can begin."}
          </p>

          <div className="p-4 rounded-xl bg-[#081826] border border-[#1E3A5F] space-y-2 text-xs text-left">
            <div className="flex justify-between items-center">
              <span className="text-[#C7D2E2] font-medium">{tossState.host_team.captain_name} (Host)</span>
              <span className="font-extrabold text-[#F4C430]">
                {tossState.host_team.player_count}/11 drafted
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#C7D2E2] font-medium">{tossState.guest_team.captain_name} (Guest)</span>
              <span className="font-extrabold text-[#138A36]">
                {tossState.guest_team.player_count}/11 drafted
              </span>
            </div>
          </div>

          <button
            onClick={() => navigate(`/draft?room=${roomCode}`)}
            className="w-full py-3.5 rounded-xl bg-gradient-to-r from-[#F4C430] to-amber-400 text-[#081826] font-black text-sm uppercase tracking-wider transition-all hover:scale-[1.02]"
          >
            Continue Player Draft
          </button>
        </div>
      </div>
    );
  }

  // Completed State: Official Ceremony Card
  if (tossState.step === "COMPLETED") {
    return (
      <div className="py-8 px-4 max-w-4xl mx-auto">
        <TossCeremony
          tossState={tossState}
          onProceedToMatch={handleProceedToMatch}
          countdownSeconds={5}
        />
      </div>
    );
  }

  // Interactive Toss Steps: CALLING and DECIDING
  const { is_current_user_caller, is_current_user_winner, caller_name, winner_name, step } = tossState;

  return (
    <div className="py-8 px-4 max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      {/* Disconnect Abandonment Modal */}
      {abandonmentNotice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#081826]/85 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <div className="max-w-md w-full p-6 sm:p-8 rounded-2xl bg-[#12263A] border-2 border-[#F4C430]/60 shadow-2xl text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-[#F4C430]/20 text-[#F4C430] mx-auto flex items-center justify-center border border-[#F4C430]/40">
              <Trophy className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-black text-white">{abandonmentNotice.title}</h2>
            <p className="text-sm font-semibold text-[#F4C430]">{abandonmentNotice.message}</p>
            <div className="flex items-center justify-center space-x-2 text-xs text-[#C7D2E2] pt-2">
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
              <p className="text-xs text-amber-300/80">Toss session is preserved. Waiting for opponent to reconnect...</p>
            </div>
          </div>
          <div className="text-right">
            <span className="font-mono text-2xl font-black text-amber-400">{disconnectCountdown}s</span>
          </div>
        </div>
      )}

      {/* Top Match Bar: Host vs Guest Captains */}
      <div className="flex flex-col sm:flex-row items-center justify-between p-4 rounded-2xl cricket-card gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-[#F4C430]/15 border border-[#F4C430]/40 flex items-center justify-center font-black text-[#F4C430] text-sm">
            H
          </div>
          <div>
            <div className="text-[11px] text-[#C7D2E2] font-semibold uppercase tracking-wider">Host Captain</div>
            <div className="text-sm font-black text-white">
              {tossState.host_team.captain_name}
            </div>
            <div className="text-[11px] text-[#F4C430] font-semibold">
              {tossState.host_team.team_name}
            </div>
          </div>
        </div>

        {/* Center Room Code Pill */}
        <div className="flex flex-col items-center">
          <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">
            Match Room
          </span>
          <span className="px-3.5 py-1 rounded-full bg-[#081826] border border-[#1E3A5F] text-[#F4C430] font-mono font-bold text-xs tracking-wider">
            {roomCode}
          </span>
        </div>

        <div className="flex items-center space-x-3 text-right">
          <div>
            <div className="text-[11px] text-[#C7D2E2] font-semibold uppercase tracking-wider">Guest Captain</div>
            <div className="text-sm font-black text-white">
              {tossState.guest_team.captain_name}
            </div>
            <div className="text-[11px] text-[#138A36] font-semibold">
              {tossState.guest_team.team_name}
            </div>
          </div>
          <div className="w-10 h-10 rounded-full bg-[#138A36]/15 border border-[#138A36]/40 flex items-center justify-center font-black text-[#138A36] text-sm">
            G
          </div>
        </div>
      </div>

      {/* Main Toss Presentation Box */}
      <div className="relative rounded-3xl cricket-card p-6 sm:p-10 shadow-2xl overflow-hidden text-center space-y-6">
        {/* Glow accent */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#0B3D91] via-[#F4C430] to-[#138A36]" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-80 h-28 bg-[#F4C430]/10 blur-3xl pointer-events-none" />

        {/* Stage Badge */}
        <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#081826] border border-[#1E3A5F] text-[#F4C430] text-xs font-black tracking-widest uppercase">
          <CircleDot className="w-3.5 h-3.5 animate-pulse text-[#F4C430]" />
          <span>
            {step === "CALLING"
              ? "Phase 1 • Calling The Toss"
              : "Phase 2 • Match Pitch Decision"}
          </span>
        </div>

        {/* 3D Coin Animation */}
        <div className="py-4">
          <Coin3D
            isFlipping={isFlipping}
            result={isFlipping ? null : tossState.coin_result || null}
            selectedCall={tossState.caller_choice || null}
          />
        </div>

        {/* STEP 1: CALLING PHASE */}
        {step === "CALLING" && (
          <div className="space-y-6 max-w-lg mx-auto">
            {is_current_user_caller ? (
              /* Current User IS the Caller */
              <div className="space-y-4 animate-in fade-in duration-300">
                <div className="space-y-1">
                  <h3 className="text-xl sm:text-2xl font-black text-white uppercase tracking-wide">
                    You Call The Toss, Captain!
                  </h3>
                  <p className="text-xs sm:text-sm text-[#C7D2E2]">
                    Call Heads or Tails before the coin flip.
                  </p>
                </div>

                {/* Heads / Tails Call Buttons */}
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <button
                    onClick={() => handleCall("HEADS")}
                    disabled={isSubmitting || isFlipping}
                    className="group relative p-5 rounded-2xl bg-[#081826] hover:bg-[#1E3A5F]/40 border-2 border-[#1E3A5F] hover:border-[#F4C430] text-white transition-all transform hover:scale-[1.03] active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none shadow-lg"
                  >
                    <div className="flex flex-col items-center space-y-2">
                      <div className="w-12 h-12 rounded-full bg-[#F4C430]/20 border border-[#F4C430]/40 flex items-center justify-center text-[#F4C430] group-hover:scale-110 transition-transform">
                        <Trophy className="w-6 h-6 stroke-[2.2]" />
                      </div>
                      <span className="text-base font-black uppercase tracking-wider text-[#F4C430]">
                        Heads
                      </span>
                      <span className="text-[11px] text-[#C7D2E2] font-medium">
                        Emblem & Trophy
                      </span>
                    </div>
                  </button>

                  <button
                    onClick={() => handleCall("TAILS")}
                    disabled={isSubmitting || isFlipping}
                    className="group relative p-5 rounded-2xl bg-[#081826] hover:bg-[#1E3A5F]/40 border-2 border-[#1E3A5F] hover:border-[#F4C430] text-white transition-all transform hover:scale-[1.03] active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none shadow-lg"
                  >
                    <div className="flex flex-col items-center space-y-2">
                      <div className="w-12 h-12 rounded-full bg-[#F4C430]/20 border border-[#F4C430]/40 flex items-center justify-center text-[#F4C430] group-hover:scale-110 transition-transform">
                        <Shield className="w-6 h-6 stroke-[2.2]" />
                      </div>
                      <span className="text-base font-black uppercase tracking-wider text-[#F4C430]">
                        Tails
                      </span>
                      <span className="text-[11px] text-[#C7D2E2] font-medium">
                        Shield & Wickets
                      </span>
                    </div>
                  </button>
                </div>
              </div>
            ) : (
              /* Current User is NOT the Caller (Waiting) */
              <div className="p-6 rounded-2xl bg-[#081826] border border-[#1E3A5F] space-y-3 animate-in fade-in duration-300">
                <div className="flex items-center justify-center space-x-2 text-[#F4C430]">
                  <Clock className="w-5 h-5 animate-pulse text-[#F4C430]" />
                  <span className="text-xs font-black tracking-widest uppercase">
                    Opponent Calling
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white">
                  Waiting for <span className="text-[#F4C430]">{caller_name}</span> to call...
                </h3>
                <p className="text-xs text-[#C7D2E2] max-w-sm mx-auto">
                  {caller_name} was designated to call Heads or Tails.
                  The result will synchronize immediately when called.
                </p>
              </div>
            )}
          </div>
        )}

        {/* STEP 2: DECIDING PHASE (Coin Flipped -> Winner Chooses Bat or Bowl) */}
        {step === "DECIDING" && (
          <div className="space-y-6 max-w-lg mx-auto">
            {/* Toss Outcome Statement */}
            <div className="p-4 rounded-2xl bg-[#F4C430]/10 border border-[#F4C430]/30 space-y-1">
              <div className="flex items-center justify-center space-x-1.5 text-[#F4C430] text-xs font-black uppercase tracking-wider">
                <CheckCircle2 className="w-4 h-4" />
                <span>Coin Landed On {tossState.coin_result}</span>
              </div>
              <h3 className="text-xl font-black text-white uppercase tracking-wide">
                <span className="text-[#F4C430]">{winner_name}</span> Won The Toss!
              </h3>
              <p className="text-xs text-[#C7D2E2]">
                Caller ({tossState.caller_name}) called{" "}
                <span className="text-white font-bold">{tossState.caller_choice}</span>.
              </p>
            </div>

            {is_current_user_winner ? (
              /* Current User IS the Winner (Select Bat or Bowl) */
              <div className="space-y-4 animate-in fade-in duration-300">
                <div className="space-y-1">
                  <h4 className="text-lg font-black text-white uppercase tracking-wide">
                    What Will You Do First?
                  </h4>
                  <p className="text-xs text-[#C7D2E2]">
                    Elect to set a high target or bowl first to exploit pitch conditions.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-1">
                  <button
                    onClick={() => handleDecision("BAT")}
                    disabled={isSubmitting}
                    className="group relative p-5 rounded-2xl bg-[#081826] hover:bg-[#F4C430]/10 border-2 border-[#1E3A5F] hover:border-[#F4C430] text-white transition-all transform hover:scale-[1.03] active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none shadow-lg text-center"
                  >
                    <div className="flex flex-col items-center space-y-2">
                      <div className="w-12 h-12 rounded-full bg-[#F4C430]/20 border border-[#F4C430]/40 flex items-center justify-center text-[#F4C430] group-hover:scale-110 transition-transform font-black text-xl">
                        🏏
                      </div>
                      <span className="text-base font-black uppercase tracking-wider text-[#F4C430]">
                        Bat First
                      </span>
                      <span className="text-[11px] text-[#C7D2E2] font-medium">
                        Set a massive 1st innings total
                      </span>
                    </div>
                  </button>

                  <button
                    onClick={() => handleDecision("BOWL")}
                    disabled={isSubmitting}
                    className="group relative p-5 rounded-2xl bg-[#081826] hover:bg-[#138A36]/10 border-2 border-[#1E3A5F] hover:border-[#138A36] text-white transition-all transform hover:scale-[1.03] active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none shadow-lg text-center"
                  >
                    <div className="flex flex-col items-center space-y-2">
                      <div className="w-12 h-12 rounded-full bg-[#138A36]/20 border border-[#138A36]/40 flex items-center justify-center text-[#138A36] group-hover:scale-110 transition-transform font-black text-xl">
                        🎯
                      </div>
                      <span className="text-base font-black uppercase tracking-wider text-[#138A36]">
                        Bowl First
                      </span>
                      <span className="text-[11px] text-[#C7D2E2] font-medium">
                        Restrict opponent & chase under lights
                      </span>
                    </div>
                  </button>
                </div>
              </div>
            ) : (
              /* Current User is NOT the Winner (Waiting for Decision) */
              <div className="p-6 rounded-2xl bg-[#081826] border border-[#1E3A5F] space-y-3 animate-in fade-in duration-300">
                <div className="flex items-center justify-center space-x-2 text-[#F4C430]">
                  <Clock className="w-5 h-5 animate-pulse" />
                  <span className="text-xs font-black tracking-widest uppercase">
                    Decision In Progress
                  </span>
                </div>
                <h4 className="text-base font-bold text-white">
                  Waiting for <span className="text-[#F4C430]">{winner_name}</span> to elect Bat or Bowl...
                </h4>
                <p className="text-xs text-[#C7D2E2] max-w-sm mx-auto">
                  The toss winner is making their tactical decision. Match will begin automatically once chosen.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

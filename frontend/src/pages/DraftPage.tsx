import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { DraftHeader } from "../components/draft/DraftHeader";
import { CandidatePool } from "../components/draft/CandidatePool";
import { BestXIPanel } from "../components/draft/BestXIPanel";
import { SlotSelectorModal } from "../components/draft/SlotSelectorModal";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { useGame } from "../contexts/GameContext";
import { useWebSocket, WebSocketEvent } from "../hooks/useWebSocket";
import { useToast } from "../components/common/Toast";
import { draftService } from "../services/draftService";
import { roomService } from "../services/roomService";
import { DraftStateResponse, Player, UserSquad } from "../types";
import { Sparkles, Trophy } from "lucide-react";

export const DraftPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const { userId, username, currentRoom, setUser, setCurrentRoom } = useGame();

  // Determine active room code from URL params, context, or localStorage
  const roomCode = useMemo(() => {
    const fromQuery = searchParams.get("room");
    if (fromQuery) return fromQuery.toUpperCase().trim();
    if (currentRoom?.room_code) return currentRoom.room_code.toUpperCase().trim();
    const fromStorage = localStorage.getItem("cricxi_room_code");
    return fromStorage ? fromStorage.toUpperCase().trim() : "";
  }, [searchParams, currentRoom]);

  // Persist room code in localStorage for reload resilience
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
  const setCurrentRoomRef = useRef(setCurrentRoom);
  setCurrentRoomRef.current = setCurrentRoom;

  // Draft State
  const [draftState, setDraftState] = useState<DraftStateResponse | null>(null);
  const draftStateRef = useRef<DraftStateResponse | null>(null);
  draftStateRef.current = draftState;

  const [remainingSeconds, setRemainingSeconds] = useState<number>(30);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Selection Modal state
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [isSubmittingPick, setIsSubmittingPick] = useState<boolean>(false);
  const [isDraftCompleted, setIsDraftCompleted] = useState<boolean>(false);

  // Disconnect recovery state
  const [isOpponentDisconnected, setIsOpponentDisconnected] = useState<boolean>(false);
  const [disconnectCountdown, setDisconnectCountdown] = useState<number | null>(null);
  const [abandonmentNotice, setAbandonmentNotice] = useState<{
    title: string;
    message: string;
    submessage: string;
  } | null>(null);

  // Single-flight navigation guard to Toss to eliminate double/duplicate navigation
  const hasNavigatedToTossRef = useRef<boolean>(false);
  const tossNavTimeoutRef = useRef<number | null>(null);

  const navigateToToss = useCallback(
    (targetCode: string) => {
      if (hasNavigatedToTossRef.current) return;
      hasNavigatedToTossRef.current = true;

      if (tossNavTimeoutRef.current) {
        clearTimeout(tossNavTimeoutRef.current);
        tossNavTimeoutRef.current = null;
      }

      const cleanCode = (targetCode || roomCode || "").trim().toUpperCase();
      if (cleanCode) {
        localStorage.setItem("cricxi_room_code", cleanCode);
        localStorage.setItem("cricxi_phase", "TOSS");
        navigate(`/toss?room=${cleanCode}`, { replace: true });
      } else {
        navigate("/toss", { replace: true });
      }
    },
    [navigate, roomCode]
  );

  // Cleanup pending toss navigation timeouts on unmount
  useEffect(() => {
    return () => {
      if (tossNavTimeoutRef.current) {
        clearTimeout(tossNavTimeoutRef.current);
        tossNavTimeoutRef.current = null;
      }
    };
  }, []);

  // Clean wipe state ONLY when room code genuinely changes (e.g. Rematch)
  const prevRoomCodeRef = useRef<string | null>(null);
  useEffect(() => {
    if (prevRoomCodeRef.current && prevRoomCodeRef.current !== roomCode) {
      setDraftState(null);
      draftStateRef.current = null;
      setIsDraftCompleted(false);
      setSelectedPlayer(null);
      setRemainingSeconds(30);
      setError(null);
    }
    prevRoomCodeRef.current = roomCode;
  }, [roomCode]);

  // Load / Sync draft state from backend REST API
  const syncDraftState = useCallback(async (isInitial = false) => {
    if (!roomCode) {
      setError("No room code found. Please join or create a room.");
      setLoading(false);
      return;
    }

    try {
      if (isInitial && !draftStateRef.current) {
        setLoading(true);
      }
      // If room is completed or abandoned, immediately redirect to lobby without rendering or flickering
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

        // If user session is unhydrated, try to re-hydrate from room players
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

      let state: DraftStateResponse;

      try {
        state = await draftService.getDraftState(roomCode, activeUserIdRef.current || undefined);
      } catch (err: any) {
        // Fallback: If draft is not initialized yet, initialize it
        state = await draftService.startDraft(roomCode);
      }

      draftStateRef.current = state;
      setDraftState(state);
      setRemainingSeconds(state.remaining_seconds);
      setIsDraftCompleted(!!state.is_finished);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load draft state.");
    } finally {
      setLoading(false);
    }
  }, [roomCode, navigate, addToast]);

  // Initial fetch on mount - guarded to run exactly once per room code
  const hasFetchedRoomRef = useRef<string | null>(null);
  useEffect(() => {
    if (roomCode && hasFetchedRoomRef.current !== roomCode) {
      hasFetchedRoomRef.current = roomCode;
      syncDraftState(true);
    }
  }, [roomCode, syncDraftState]);

  // Handle incoming real-time WebSocket events
  const handleWebSocketMessage = useCallback(
    (event: WebSocketEvent) => {
      switch (event.type) {
        case "timer_tick": {
          const seconds =
            typeof event.remaining === "number"
              ? event.remaining
              : typeof event.remaining_seconds === "number"
                ? event.remaining_seconds
                : null;
          if (seconds !== null) {
            setRemainingSeconds(seconds);
          }
          break;
        }

        case "draft_started":
        case "round_generated": {
          const roundNum = event.round_number || event.current_round;
          const country = event.country || event.round_country;
          const decade = event.decade || event.round_decade;
          if (roundNum && country) {
            addToast(`Round ${roundNum}: ${country} ${decade ? `${decade}s` : ""}!`, "info");
          }
          if (event.draft_state) {
            draftStateRef.current = event.draft_state;
            setDraftState(event.draft_state);
            setIsDraftCompleted(!!event.draft_state.is_finished);
            setRemainingSeconds(event.draft_state.remaining_seconds);
          }
          break;
        }

        case "player_selected":
        case "player_auto_selected": {
          const pick = event.pick || {};
          const playerName = pick.player_name || event.player_name || "Player";
          const pos = pick.batting_position || event.batting_position;
          const isAuto = event.is_auto || event.type === "player_auto_selected";

          if (isAuto) {
            addToast(`Time expired! System auto-picked ${playerName} (Pos ${pos})`, "warning");
          } else {
            addToast(`${playerName} drafted at Position ${pos}!`, "success");
          }
          if (event.draft_state) {
            draftStateRef.current = event.draft_state;
            setDraftState(event.draft_state);
            setRemainingSeconds(event.draft_state.remaining_seconds);
          }
          break;
        }

        case "player_locked":
          if (event.draft_state) {
            draftStateRef.current = event.draft_state;
            setDraftState(event.draft_state);
          }
          break;

        case "round_finished": {
          const roundNum = event.round_number;
          if (roundNum) {
            addToast(`Round ${roundNum} complete!`, "info");
          }
          break;
        }

        case "draft_finished":
        case "toss_started":
          setIsDraftCompleted(true);
          if (event.draft_state) {
            draftStateRef.current = event.draft_state;
            setDraftState(event.draft_state);
          }
          if (!hasNavigatedToTossRef.current) {
            addToast("Draft Complete! Both teams locked. Proceeding to Toss...", "success");
            if (tossNavTimeoutRef.current) clearTimeout(tossNavTimeoutRef.current);
            tossNavTimeoutRef.current = window.setTimeout(() => {
              navigateToToss(roomCode);
            }, 1800);
          }
          break;

        case "draft_state_updated":
        case "reconnected":
          if (event.draft_state) {
            draftStateRef.current = event.draft_state;
            setDraftState(event.draft_state);
            setIsDraftCompleted(!!event.draft_state.is_finished);
            if (typeof event.draft_state.remaining_seconds === "number") {
              setRemainingSeconds(event.draft_state.remaining_seconds);
            }
          }
          break;

        case "player_disconnected":
          if (event.user_id && event.user_id === activeUserId) {
            // Disconnected player should never see overlay about themselves
            return;
          }
          setIsOpponentDisconnected(true);
          setDisconnectCountdown(typeof event.seconds_remaining === "number" ? event.seconds_remaining : 30);
          addToast("Opponent disconnected. Draft timer paused.", "warning");
          break;

        case "disconnect_countdown_tick":
          if (event.user_id && event.user_id === activeUserId) {
            return;
          }
          setIsOpponentDisconnected(true);
          if (typeof event.seconds_remaining === "number") {
            setDisconnectCountdown(event.seconds_remaining);
          }
          break;

        case "player_reconnected":
          setIsOpponentDisconnected(false);
          setDisconnectCountdown(null);
          addToast("Opponent reconnected! Draft resuming...", "success");
          break;

        case "disconnect_timeout":
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
          break;

        case "match_abandoned":
          setIsOpponentDisconnected(false);
          setDisconnectCountdown(null);
          localStorage.removeItem("cricxi_room_code");
          localStorage.removeItem("cricxi_phase");
          navigate("/lobby", { replace: true });
          break;

        case "player_left":
          if (event.user_id && event.user_id === activeUserId) return;
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
          break;

        default:
          break;
      }
    },
    [syncDraftState, addToast, navigate, roomCode, navigateToToss]
  );

  // Stable socket connection parameters: only roomCode and activeUserId
  const isReadyForSocket = !!roomCode && !!activeUserId;

  const handleReconnectRef = useRef<(() => void) | undefined>(undefined);

  const { sendMessage } = useWebSocket(
    isReadyForSocket ? roomCode : null,
    isReadyForSocket ? activeUserId : null,
    {
      enabled: isReadyForSocket,
      onMessage: handleWebSocketMessage,
      onReconnect: () => handleReconnectRef.current?.(),
      onError: (err) => addToast(err, "error"),
    }
  );

  handleReconnectRef.current = () => {
    addToast("Reconnected to live draft session.", "info");
    sendMessage({ type: "request_draft_state" });
  };

  // Derived user squads
  const mySquad: UserSquad | null = useMemo(() => {
    if (!draftState || !activeUserId) return null;
    if (draftState.user_squads && draftState.user_squads[activeUserId]) {
      return draftState.user_squads[activeUserId];
    }
    if (draftState.host_squad?.user_id === activeUserId) return draftState.host_squad;
    if (draftState.guest_squad?.user_id === activeUserId) return draftState.guest_squad;
    return null;
  }, [draftState, activeUserId]);

  const opponentSquad: UserSquad | null = useMemo(() => {
    if (!draftState || !activeUserId) return null;
    if (draftState.user_squads) {
      const oppId = Object.keys(draftState.user_squads).find((id) => id !== activeUserId);
      if (oppId) return draftState.user_squads[oppId];
    }
    if (draftState.host_squad && draftState.host_squad.user_id !== activeUserId) {
      return draftState.host_squad;
    }
    if (draftState.guest_squad && draftState.guest_squad.user_id !== activeUserId) {
      return draftState.guest_squad;
    }
    return null;
  }, [draftState, activeUserId]);

  const opponentUsername = opponentSquad?.username || "Opponent";
  const myUsername = mySquad?.username || username || "You";

  const isMyTurn = draftState?.current_picker_id === activeUserId && !draftState?.is_finished;

  // Candidates list guaranteed to be valid Player[]
  const candidates: Player[] = useMemo(() => {
    if (!draftState) return [];
    if (Array.isArray(draftState.candidates) && draftState.candidates.length > 0) {
      return draftState.candidates;
    }
    if (Array.isArray(draftState.available_pool) && draftState.available_pool.length > 0) {
      return draftState.available_pool;
    }
    if (Array.isArray(draftState.current_pool) && draftState.current_pool.length > 0) {
      return draftState.current_pool;
    }
    return [];
  }, [draftState]);

  // Drafted player IDs guaranteed to be valid number[]
  const draftedIds: number[] = useMemo(() => {
    if (!draftState) return [];
    if (Array.isArray(draftState.drafted_player_ids)) {
      return draftState.drafted_player_ids;
    }
    if (Array.isArray(draftState.all_picks)) {
      return draftState.all_picks.map((p) => p.player_id);
    }
    return [];
  }, [draftState]);

  // Handle player selection confirmation from modal
  const handleConfirmPick = async (playerId: number, battingPosition: number) => {
    if (!roomCode || !activeUserId) return;
    setIsSubmittingPick(true);

    try {
      // Send pick via REST API
      const result = await draftService.makePick(roomCode, {
        user_id: activeUserId,
        player_id: playerId,
        batting_position: battingPosition,
      });

      setSelectedPlayer(null);

      // Also notify WebSocket
      sendMessage({
        type: "make_pick",
        player_id: playerId,
        batting_position: battingPosition,
      });

      if (result.is_finished) {
        setIsDraftCompleted(true);
        addToast("Draft Complete! Preparing Toss...", "success");
        // Authoritative WebSocket draft_finished/toss_started handles navigation for both players.
        // Fallback timeout in case WebSocket was delayed or disconnected:
        if (!hasNavigatedToTossRef.current) {
          if (tossNavTimeoutRef.current) clearTimeout(tossNavTimeoutRef.current);
          tossNavTimeoutRef.current = window.setTimeout(() => {
            navigateToToss(roomCode);
          }, 3500);
        }
      } else {
        setDraftState(result);
        setRemainingSeconds(result.remaining_seconds);
      }
    } catch (err: any) {
      addToast(err.message || "Failed to submit draft pick.", "error");
    } finally {
      setIsSubmittingPick(false);
    }
  };

  // Proper loading state until draft state is loaded
  if (loading || !draftState) {
    return <LoadingSpinner label="Loading Draft..." />;
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto text-center py-16 px-4">
        <div className="cricket-card p-8 space-y-4">
          <h3 className="text-xl font-black text-white tracking-tight">Draft Unavailable</h3>
          <p className="text-sm text-[#C7D2E2]">
            {error || "Unable to synchronize with the draft session."}
          </p>
          <div className="pt-2 flex justify-center space-x-3">
            <button
              onClick={() => syncDraftState()}
              className="px-5 py-2.5 text-xs font-black rounded-xl bg-gradient-to-r from-[#0B3D91] to-[#1E3A5F] text-white border border-[#F4C430]/40 hover:scale-[1.02] transition-transform"
            >
              Retry
            </button>
            <button
              onClick={() => navigate("/lobby" + (roomCode ? `?room=${roomCode}` : ""))}
              className="px-5 py-2.5 text-xs font-bold rounded-xl bg-[#081826] border border-[#1E3A5F] text-[#C7D2E2] hover:text-white transition-colors"
            >
              Return to Lobby
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 py-4 px-2 sm:px-4 max-w-7xl mx-auto">
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

      {/* Draft Completion Celebration Banner */}
      {isDraftCompleted && (
        <div className="p-5 rounded-2xl bg-gradient-to-r from-emerald-500/20 via-accent/20 to-emerald-500/20 border border-emerald-500/40 text-center space-y-2 animate-in fade-in zoom-in-95 duration-500">
          <div className="flex items-center justify-center space-x-2 text-emerald-400">
            <Trophy className="w-6 h-6 animate-bounce" />
            <span className="text-lg font-black uppercase tracking-wider">
              Draft Finished!
            </span>
            <Sparkles className="w-6 h-6 animate-pulse" />
          </div>
          <p className="text-sm text-slate-200">
            Both players have successfully locked in their 11-player squads. Navigating to the Toss...
          </p>
        </div>
      )}

      {/* Opponent Disconnected Banner (only for connected opponent) */}
      {isOpponentDisconnected && disconnectCountdown !== null && (
        <div className="p-4 rounded-xl bg-amber-500/15 border border-amber-500/40 text-amber-200 flex items-center justify-between shadow-lg backdrop-blur-sm animate-pulse">
          <div className="flex items-center space-x-3">
            <span className="w-3 h-3 rounded-full bg-amber-400 animate-ping" />
            <div>
              <p className="font-bold text-sm">Opponent Disconnected</p>
              <p className="text-xs text-amber-300/80">Draft timer is paused. Waiting for opponent to reconnect...</p>
            </div>
          </div>
          <div className="text-right">
            <span className="font-mono text-2xl font-black text-amber-400">{disconnectCountdown}s</span>
          </div>
        </div>
      )}

      {/* Header: Round, Decade+Country, Turn & Timer */}
      <DraftHeader
        currentRound={draftState.current_round}
        totalRounds={draftState.total_rounds || 11}
        roundCountry={draftState.round_country}
        roundDecade={draftState.round_decade}
        remainingSeconds={remainingSeconds}
        isMyTurn={isMyTurn}
        currentPickerName={draftState.current_picker_name}
        countryHistory={draftState.country_history || []}
      />

      {/* Main Drafting Arena Layout: Candidate Pool + Best XI Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Candidate Player Pool (2 cols on large screen) */}
        <div className="lg:col-span-2">
          <CandidatePool
            candidates={candidates}
            draftedIds={draftedIds}
            isMyTurn={isMyTurn}
            onSelectPlayer={(player) => setSelectedPlayer(player)}
          />
        </div>

        {/* Best XI Lineup Panel (1 col on large screen) */}
        <div className="lg:col-span-1">
          <BestXIPanel
            mySquad={mySquad}
            opponentSquad={opponentSquad}
            myUsername={myUsername}
            opponentUsername={opponentUsername}
          />
        </div>
      </div>

      {/* Batting Position Slot Selector Modal */}
      <SlotSelectorModal
        player={selectedPlayer}
        mySquad={mySquad}
        isOpen={!!selectedPlayer}
        isSubmitting={isSubmittingPick}
        onClose={() => setSelectedPlayer(null)}
        onConfirm={handleConfirmPick}
      />
    </div>
  );
};

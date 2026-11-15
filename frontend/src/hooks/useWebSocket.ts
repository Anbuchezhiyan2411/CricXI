import { useEffect, useRef, useState, useCallback } from "react";
import { WS_BASE_URL } from "../utils/constants";
import { Room } from "../types";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

export interface WebSocketEvent {
  type: string;
  room?: Room | null;
  player_id?: string;
  username?: string;
  message?: string;
  disconnected?: boolean;
  [key: string]: any;
}

export interface UseWebSocketOptions {
  enabled?: boolean;
  onMessage?: (event: WebSocketEvent) => void;
  onError?: (errorMsg: string) => void;
  onReconnect?: () => void;
}

export function useWebSocket(
  roomCode?: string | null,
  playerId?: string | null,
  options: UseWebSocketOptions = {}
) {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<WebSocketEvent | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const isManuallyClosedRef = useRef<boolean>(false);
  const pingIntervalRef = useRef<number | null>(null);
  const stableTimerRef = useRef<number | null>(null);
  const wasUnexpectedlyDisconnectedRef = useRef<boolean>(false);

  const { enabled = true, onMessage, onError, onReconnect } = options;
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);
  const onReconnectRef = useRef(onReconnect);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onErrorRef.current = onError;
    onReconnectRef.current = onReconnect;
  }, [onMessage, onError, onReconnect]);

  const cleanRoom = roomCode ? roomCode.trim().toUpperCase() : null;
  const cleanPlayerId = playerId ? playerId.trim() : null;

  const connect = useCallback(() => {
    // If not enabled or parameters are missing, ensure closed and disconnect
    if (!enabled || !cleanRoom || !cleanPlayerId) {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (socketRef.current) {
        const s = socketRef.current;
        socketRef.current = null;
        s.close(1000, "Disabled or missing parameters");
      }
      setStatus("disconnected");
      return;
    }

    const cleanBase = WS_BASE_URL.replace(/^http/, "ws").replace(/\/$/, "");
    const targetUrl = `${cleanBase}/ws/${cleanRoom}/${cleanPlayerId}`;

    // If already connected or connecting to the EXACT same target, do NOT recreate
    if (socketRef.current) {
      const current = socketRef.current;
      if (
        (current.readyState === WebSocket.OPEN || current.readyState === WebSocket.CONNECTING) &&
        current.url === targetUrl
      ) {
        return;
      }
      // Otherwise replace
      socketRef.current = null;
      current.close(1000, "Replacing connection");
    }

    isManuallyClosedRef.current = false;

    try {
      if (wasUnexpectedlyDisconnectedRef.current) {
        setStatus("reconnecting");
      }

      const ws = new WebSocket(targetUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        // Discard stale socket events
        if (socketRef.current !== ws) return;

        setStatus("connected");

        // Clear any pending reconnect
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }

        // Trigger onReconnect ONLY on genuine recovery from unexpected disconnection
        if (wasUnexpectedlyDisconnectedRef.current) {
          wasUnexpectedlyDisconnectedRef.current = false;
          if (onReconnectRef.current) {
            onReconnectRef.current();
          }
        }

        // Reset backoff after 3 seconds of a stable open connection
        if (stableTimerRef.current) clearTimeout(stableTimerRef.current);
        stableTimerRef.current = window.setTimeout(() => {
          if (socketRef.current === ws && ws.readyState === WebSocket.OPEN) {
            reconnectAttemptsRef.current = 0;
          }
        }, 3000);

        // Setup client heartbeat every 3 seconds
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        const sendHeartbeat = () => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "heartbeat", timestamp: Date.now(), player_id: cleanPlayerId }));
          }
        };
        pingIntervalRef.current = window.setInterval(sendHeartbeat, 3000);

        // Send immediate heartbeat on visibility restoration (tab switch back)
        const handleVisibilityChange = () => {
          if (document.visibilityState === "visible" && ws.readyState === WebSocket.OPEN) {
            sendHeartbeat();
          }
        };
        document.addEventListener("visibilitychange", handleVisibilityChange);
      };

      ws.onmessage = (event) => {
        // Discard stale socket events
        if (socketRef.current !== ws) return;

        try {
          const data: WebSocketEvent = JSON.parse(event.data);
          if (data.type === "pong" || data.type === "heartbeat_ack") return;

          setLastMessage(data);
          if (onMessageRef.current) {
            onMessageRef.current(data);
          }

          if (data.type === "connection_error") {
            if (onErrorRef.current) {
              onErrorRef.current(data.message || "Connection error occurred.");
            }
          }
        } catch (err) {
          console.warn("Unparseable WebSocket payload:", event.data);
        }
      };

      ws.onclose = (event: CloseEvent) => {
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        if (stableTimerRef.current) clearTimeout(stableTimerRef.current);

        // Discard stale socket events (e.g. from cleanup of an old socket)
        if (socketRef.current !== ws) {
          return;
        }

        // Clean up current reference
        socketRef.current = null;

        const isPermanentError =
          event.code === 4003 || event.code === 4004 || event.code === 1000;

        if (!isManuallyClosedRef.current && !isPermanentError) {
          wasUnexpectedlyDisconnectedRef.current = true;
          setStatus("reconnecting");
          // Exponential backoff reconnect: 1s, 1.5s, 2.25s, up to 8s
          const delay = Math.min(1000 * Math.pow(1.5, reconnectAttemptsRef.current), 8000);
          reconnectAttemptsRef.current += 1;

          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, delay);
        } else {
          setStatus("disconnected");
        }
      };

      ws.onerror = (err) => {
        if (socketRef.current !== ws) return;
        console.warn("WebSocket error:", err);
        ws.close();
      };
    } catch (err) {
      console.error("Failed to establish WebSocket:", err);
      setStatus("disconnected");
    }
  }, [enabled, cleanRoom, cleanPlayerId]);

  useEffect(() => {
    connect();

    return () => {
      isManuallyClosedRef.current = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (stableTimerRef.current) clearTimeout(stableTimerRef.current);
      if (socketRef.current) {
        const s = socketRef.current;
        socketRef.current = null;
        s.close(1000, "Component unmounted");
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: Record<string, any>) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    } else {
      console.warn("Cannot send message: WebSocket is not open.");
    }
  }, []);

  const toggleReady = useCallback(() => {
    sendMessage({ type: "toggle_ready" });
  }, [sendMessage]);

  const setReady = useCallback((isReady: boolean) => {
    sendMessage({ type: isReady ? "player_ready" : "player_not_ready" });
  }, [sendMessage]);

  const startGame = useCallback(() => {
    sendMessage({ type: "game_start" });
  }, [sendMessage]);

  const leaveRoom = useCallback(() => {
    isManuallyClosedRef.current = true;
    sendMessage({ type: "player_left", intentional: true });
    if (socketRef.current) {
      const s = socketRef.current;
      socketRef.current = null;
      s.close(1000, "Player left room");
    }
    setStatus("disconnected");
  }, [sendMessage]);

  return {
    status,
    isConnected: status === "connected",
    isReconnecting: status === "reconnecting",
    lastMessage,
    sendMessage,
    toggleReady,
    setReady,
    startGame,
    leaveRoom,
    reconnect: connect,
  };
}

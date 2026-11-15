import React, { createContext, useContext, useState, useMemo } from "react";
import { Room, PlayerInRoom } from "../types";

interface GameContextType {
  userId: string | null;
  username: string | null;
  currentRoom: Room | null;
  isHost: boolean;
  isReady: boolean;
  opponent: PlayerInRoom | null;
  opponentReady: boolean;
  canStart: boolean;
  setUser: (id: string, name: string) => void;
  setCurrentRoom: (room: Room | null) => void;
  clearSession: () => void;
}

const GameContext = createContext<GameContextType | undefined>(undefined);

export const GameProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Always restore persistent player identity from localStorage
  const [userId, setUserId] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem("cricxi_user_id") : null
  );
  const [username, setUsername] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem("cricxi_username") : null
  );
  const [currentRoom, setCurrentRoomState] = useState<Room | null>(null);

  const setCurrentRoom = (room: Room | null) => {
    setCurrentRoomState(room);
    if (room?.room_code) {
      localStorage.setItem("cricxi_room_code", room.room_code);
    }
    if (room?.status) {
      localStorage.setItem("cricxi_phase", room.status);
    }
  };

  const setUser = (id: string, name: string) => {
    const trimmed = name.trim();
    setUserId(id);
    setUsername(trimmed);
    localStorage.setItem("cricxi_user_id", id);
    localStorage.setItem("cricxi_username", trimmed);
  };

  const clearSession = () => {
    setUserId(null);
    setUsername(null);
    setCurrentRoomState(null);
    localStorage.removeItem("cricxi_user_id");
    localStorage.removeItem("cricxi_username");
    localStorage.removeItem("cricxi_room_code");
    localStorage.removeItem("cricxi_phase");
  };

  // Derived player status
  const me = useMemo(() => {
    if (!currentRoom || !userId) return null;
    return currentRoom.players.find((p) => p.user_id === userId) || null;
  }, [currentRoom, userId]);

  const opponent = useMemo(() => {
    if (!currentRoom || !userId) return null;
    return currentRoom.players.find((p) => p.user_id !== userId) || null;
  }, [currentRoom, userId]);

  const isHost = me?.is_host ?? false;
  const isReady = me?.is_ready ?? false;
  const opponentReady = opponent?.is_ready ?? false;

  // Host can start ONLY when both players are in room AND both are ready
  const canStart = isHost && currentRoom?.players.length === 2 && isReady && opponentReady;

  return (
    <GameContext.Provider
      value={{
        userId,
        username,
        currentRoom,
        isHost,
        isReady,
        opponent,
        opponentReady,
        canStart,
        setUser,
        setCurrentRoom,
        clearSession,
      }}
    >
      {children}
    </GameContext.Provider>
  );
};

export const useGame = () => {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error("useGame must be used within a GameProvider");
  }
  return context;
};

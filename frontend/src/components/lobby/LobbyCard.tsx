import React, { useState } from "react";
import {
  Copy,
  Check,
  Users,
  Crown,
  Play,
  LogOut,
  Wifi,
  WifiOff,
  Clock,
  Sparkles,
} from "lucide-react";
import { Button } from "../common/Button";
import { Badge } from "../common/Badge";
import { Room } from "../../types";
import { copyToClipboard } from "../../utils/helpers";
import { ConnectionStatus } from "../../hooks/useWebSocket";

interface LobbyCardProps {
  room: Room;
  currentUserId?: string | null;
  connectionStatus?: ConnectionStatus;
  isStarting?: boolean;
  onReadyToggle?: () => void;
  onStartGame?: () => void;
  onLeaveRoom?: () => void;
}

export const LobbyCard: React.FC<LobbyCardProps> = ({
  room,
  currentUserId,
  connectionStatus = "connected",
  isStarting = false,
  onReadyToggle,
  onStartGame,
  onLeaveRoom,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopyCode = async () => {
    const success = await copyToClipboard(room.room_code);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    }
  };

  const hostPlayer = room.players.find((p) => p.is_host);
  const guestPlayer = room.players.find((p) => !p.is_host);
  const me = room.players.find((p) => p.user_id === currentUserId);
  const isMeHost = me?.is_host ?? false;

  const bothReady =
    room.players.length === 2 && room.players.every((p) => p.is_ready);

  return (
    <div className="max-w-2xl mx-auto space-y-6 shadow-2xl rounded-[20px] border border-[#1E3A5F] bg-[#12263A] p-6 sm:p-8 backdrop-blur-xl relative overflow-hidden">
      {/* Ambient Sports Stadium Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-28 bg-[#0B3D91]/25 blur-3xl pointer-events-none" />

      {/* Header: Room Code and Connection Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-[#1E3A5F]/80 gap-4 relative z-10">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[11px] uppercase font-black tracking-widest text-[#C7D2E2]">
              Multiplayer Match Code
            </span>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#1E3A5F]" />
            <div className="flex items-center space-x-1 text-xs">
              {connectionStatus === "connected" && (
                <span className="text-[#138A36] flex items-center space-x-1 font-bold">
                  <Wifi className="w-3.5 h-3.5 text-[#138A36]" />
                  <span>Real-Time Sync</span>
                </span>
              )}
              {connectionStatus === "reconnecting" && (
                <span className="text-[#F4C430] flex items-center space-x-1 font-bold animate-pulse">
                  <Clock className="w-3.5 h-3.5 text-[#F4C430]" />
                  <span>Reconnecting...</span>
                </span>
              )}
              {connectionStatus === "disconnected" && (
                <span className="text-[#E53935] flex items-center space-x-1 font-bold">
                  <WifiOff className="w-3.5 h-3.5 text-[#E53935]" />
                  <span>Disconnected</span>
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-3 mt-2">
            <span className="text-3xl sm:text-4xl font-mono font-black text-[#F4C430] tracking-widest bg-[#081826] px-5 py-2 rounded-[14px] border border-[#1E3A5F] shadow-inner">
              {room.room_code}
            </span>
            <Button
              variant="secondary"
              size="md"
              onClick={handleCopyCode}
              className="flex items-center space-x-2 border-[#1E3A5F] bg-[#081826]/80 hover:bg-[#1E3A5F] text-white py-2.5 px-4"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-[#138A36]" />
                  <span className="text-[#138A36] font-bold">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 text-[#C7D2E2]" />
                  <span>Copy Code</span>
                </>
              )}
            </Button>
          </div>
        </div>

        <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center">
          <Badge
            variant={bothReady ? "accent" : "outline"}
            className={`text-xs px-3.5 py-1 font-black uppercase tracking-wider rounded-full ${
              bothReady
                ? "bg-[#138A36]/20 border-[#138A36] text-[#138A36]"
                : "bg-[#081826] border-[#1E3A5F] text-[#C7D2E2]"
            }`}
          >
            {room.status === "WAITING" ? (bothReady ? "Ready to Start" : "Waiting for Players") : room.status}
          </Badge>
          <div className="text-xs text-[#C7D2E2] mt-2 flex items-center space-x-1.5 font-bold">
            <Users className="w-4 h-4 text-[#1E3A5F]" />
            <span>{room.players.length} / 2 Players in Room</span>
          </div>
        </div>
      </div>

      {/* Players Lineup */}
      <div className="space-y-3 relative z-10">
        <h3 className="text-xs font-black text-[#C7D2E2] uppercase tracking-wider">
          Match Competitors
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Host Card */}
          <div
            className={`p-4 rounded-[16px] border transition-all ${
              hostPlayer?.is_ready
                ? "bg-[#138A36]/10 border-[#138A36]/50 shadow-lg shadow-[#138A36]/10"
                : "bg-[#081826]/90 border-[#1E3A5F]"
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-1.5">
                <Crown className="w-4 h-4 text-[#F4C430]" />
                <span className="text-xs font-black uppercase tracking-wider text-[#F4C430]">
                  Host Captain
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span
                  className={`inline-block w-2 h-2 rounded-full ${
                    hostPlayer?.is_connected ? "bg-[#138A36] animate-pulse" : "bg-slate-600"
                  }`}
                  title={hostPlayer?.is_connected ? "Connected" : "Disconnected"}
                />
                <span
                  className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                    hostPlayer?.is_ready
                      ? "bg-[#138A36]/20 text-[#138A36] border-[#138A36]/40"
                      : "bg-[#12263A] text-[#C7D2E2] border-[#1E3A5F]"
                  }`}
                >
                  {hostPlayer?.is_ready ? "Ready" : "Not Ready"}
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-3.5">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#0B3D91] to-[#1E3A5F] border border-[#F4C430]/30 flex items-center justify-center font-black text-base text-white shadow-md">
                {hostPlayer?.username.substring(0, 2).toUpperCase() || "??"}
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <span className="font-black text-white text-base">
                    {hostPlayer?.username || "Host"}
                  </span>
                  {hostPlayer?.user_id === currentUserId && (
                    <span className="text-[11px] text-[#F4C430] font-black">(You)</span>
                  )}
                </div>
                <div className="text-[11px] text-[#C7D2E2] font-medium">
                  {hostPlayer?.is_connected ? "Ready in Lobby" : "Offline"}
                </div>
              </div>
            </div>
          </div>

          {/* Guest Card */}
          {guestPlayer ? (
            <div
              className={`p-4 rounded-[16px] border transition-all ${
                guestPlayer.is_ready
                  ? "bg-[#138A36]/10 border-[#138A36]/50 shadow-lg shadow-[#138A36]/10"
                  : "bg-[#081826]/90 border-[#1E3A5F]"
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-black uppercase tracking-wider text-[#C7D2E2]">
                  Challenger
                </span>
                <div className="flex items-center space-x-2">
                  <span
                    className={`inline-block w-2 h-2 rounded-full ${
                      guestPlayer.is_connected ? "bg-[#138A36] animate-pulse" : "bg-slate-600"
                    }`}
                    title={guestPlayer.is_connected ? "Connected" : "Disconnected"}
                  />
                  <span
                    className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                      guestPlayer.is_ready
                        ? "bg-[#138A36]/20 text-[#138A36] border-[#138A36]/40"
                        : "bg-[#12263A] text-[#C7D2E2] border-[#1E3A5F]"
                    }`}
                  >
                    {guestPlayer.is_ready ? "Ready" : "Not Ready"}
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-3.5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#1E3A5F] to-[#12263A] border border-[#1E3A5F] flex items-center justify-center font-black text-base text-white shadow-md">
                  {guestPlayer.username.substring(0, 2).toUpperCase()}
                </div>
                <div>
                  <div className="flex items-center space-x-1.5">
                    <span className="font-black text-white text-base">
                      {guestPlayer.username}
                    </span>
                    {guestPlayer.user_id === currentUserId && (
                      <span className="text-[11px] text-[#F4C430] font-black">(You)</span>
                    )}
                  </div>
                  <div className="text-[11px] text-[#C7D2E2] font-medium">
                    {guestPlayer.is_connected ? "Ready in Lobby" : "Offline"}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Waiting for Guest animation card */
            <div className="p-5 rounded-[16px] border-2 border-dashed border-[#1E3A5F] bg-[#081826]/60 flex flex-col items-center justify-center text-center space-y-2 min-h-[110px]">
              <div className="flex items-center space-x-2 text-[#F4C430] text-sm font-black uppercase tracking-wider animate-pulse">
                <Sparkles className="w-4 h-4 text-[#F4C430]" />
                <span>Awaiting Opponent...</span>
              </div>
              <p className="text-xs text-[#C7D2E2] max-w-xs font-medium">
                Share code <span className="font-mono text-[#F4C430] font-black px-1.5 py-0.5 rounded bg-[#12263A]">{room.room_code}</span> to challenge a friend!
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="pt-4 border-t border-[#1E3A5F]/80 space-y-4 relative z-10">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {/* Ready Button */}
          {onReadyToggle && (
            <Button
              variant={me?.is_ready ? "secondary" : "success"}
              className="w-full py-3.5 font-black text-xs uppercase tracking-wider flex items-center justify-center space-x-2 shadow-lg"
              onClick={onReadyToggle}
            >
              <Check className="w-4 h-4" />
              <span>{me?.is_ready ? "Cancel Ready" : "Mark Ready"}</span>
            </Button>
          )}

          {/* Start Game Button (Host Only) */}
          {isMeHost && (
            <Button
              variant="gold"
              disabled={!bothReady || isStarting}
              isLoading={isStarting}
              onClick={onStartGame}
              className={`w-full py-3.5 font-black text-xs uppercase tracking-wider flex items-center justify-center space-x-2 shadow-lg ${
                bothReady
                  ? "bg-gradient-to-r from-[#F4C430] to-[#D4A516] text-[#081826] shadow-[#F4C430]/30 hover:scale-[1.03]"
                  : "bg-[#1E3A5F] text-slate-500 border border-slate-700 cursor-not-allowed opacity-60"
              }`}
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Start Match</span>
            </Button>
          )}

          {/* Guest waiting placeholder indicator when guest is ready */}
          {!isMeHost && (
            <div className="flex items-center justify-center px-4 py-3 rounded-[14px] bg-[#081826] border border-[#1E3A5F] text-xs text-[#C7D2E2] font-semibold">
              {bothReady
                ? "Both players ready! Waiting for Host to start..."
                : "Waiting for both players to mark Ready..."}
            </div>
          )}
        </div>

        {/* Start Game Requirement Helper notice for Host */}
        {isMeHost && !bothReady && (
          <p className="text-center text-xs text-[#C7D2E2] font-medium">
            {room.players.length < 2
              ? "Cannot start: opponent has not joined yet."
              : !hostPlayer?.is_ready
                ? "You must mark yourself Ready before starting."
                : "Waiting for opponent to mark Ready."}
          </p>
        )}

        {/* Leave Room Button */}
        {onLeaveRoom && (
          <div className="pt-1 flex justify-center">
            <button
              onClick={onLeaveRoom}
              className="text-xs text-[#E53935]/80 hover:text-[#E53935] font-bold uppercase tracking-wider flex items-center space-x-1.5 py-1.5 px-3 rounded-lg hover:bg-red-500/10 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Leave Room</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

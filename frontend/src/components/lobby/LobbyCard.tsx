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
import { Card } from "../common/Card";
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
    <Card className="max-w-2xl mx-auto space-y-6 shadow-2xl border-slate-800 bg-slate-900/90 backdrop-blur-md">
      {/* Header: Room Code and Connection Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[11px] uppercase font-bold tracking-widest text-slate-400">
              Room Friend Code
            </span>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-600" />
            <div className="flex items-center space-x-1 text-xs">
              {connectionStatus === "connected" && (
                <span className="text-accent flex items-center space-x-1 font-medium">
                  <Wifi className="w-3.5 h-3.5 text-accent" />
                  <span>Live Sync</span>
                </span>
              )}
              {connectionStatus === "reconnecting" && (
                <span className="text-highlight flex items-center space-x-1 font-medium animate-pulse">
                  <Clock className="w-3.5 h-3.5 text-highlight" />
                  <span>Reconnecting...</span>
                </span>
              )}
              {connectionStatus === "disconnected" && (
                <span className="text-red-400 flex items-center space-x-1 font-medium">
                  <WifiOff className="w-3.5 h-3.5 text-red-400" />
                  <span>Disconnected</span>
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-3 mt-1.5">
            <span className="text-3xl sm:text-4xl font-mono font-black text-highlight tracking-widest bg-slate-950/70 px-4 py-1.5 rounded-xl border border-slate-800">
              {room.room_code}
            </span>
            <Button
              variant="secondary"
              size="md"
              onClick={handleCopyCode}
              className="flex items-center space-x-1.5 border-slate-700 bg-slate-800/80 hover:bg-slate-700"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-accent" />
                  <span className="text-accent font-semibold">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 text-slate-300" />
                  <span>Copy Code</span>
                </>
              )}
            </Button>
          </div>
        </div>

        <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center">
          <Badge variant={bothReady ? "accent" : "outline"} className="text-xs px-3 py-1">
            {room.status === "WAITING" ? (bothReady ? "Ready to Start" : "In Lobby") : room.status}
          </Badge>
          <div className="text-xs text-slate-400 mt-2 flex items-center space-x-1.5 font-medium">
            <Users className="w-4 h-4 text-slate-500" />
            <span>{room.players.length} / 2 Players</span>
          </div>
        </div>
      </div>

      {/* Players Lineup */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
          Draft Opponents
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {/* Host Card */}
          <div
            className={`p-4 rounded-xl border transition-all ${hostPlayer?.is_ready
              ? "bg-accent/5 border-accent/40 shadow-lg shadow-accent/5"
              : "bg-slate-950/60 border-slate-800"
              }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-1.5">
                <Crown className="w-4 h-4 text-highlight" />
                <span className="text-xs font-bold uppercase tracking-wider text-highlight">
                  Host
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span
                  className={`inline-block w-2 h-2 rounded-full ${hostPlayer?.is_connected ? "bg-accent animate-pulse" : "bg-slate-600"
                    }`}
                  title={hostPlayer?.is_connected ? "Connected" : "Disconnected"}
                />
                <Badge variant={hostPlayer?.is_ready ? "accent" : "outline"}>
                  {hostPlayer?.is_ready ? "Ready" : "Not Ready"}
                </Badge>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-surface to-slate-800 border border-slate-700 flex items-center justify-center font-black text-base text-white shadow-inner">
                {hostPlayer?.username.substring(0, 2).toUpperCase() || "??"}
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <span className="font-bold text-white text-base">
                    {hostPlayer?.username || "Host"}
                  </span>
                  {hostPlayer?.user_id === currentUserId && (
                    <span className="text-[11px] text-accent font-semibold">(You)</span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400">
                  {hostPlayer?.is_connected ? "Connected" : "Offline"}
                </div>
              </div>
            </div>
          </div>

          {/* Guest Card */}
          {guestPlayer ? (
            <div
              className={`p-4 rounded-xl border transition-all ${guestPlayer.is_ready
                ? "bg-accent/5 border-accent/40 shadow-lg shadow-accent/5"
                : "bg-slate-950/60 border-slate-800"
                }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Challenger
                </span>
                <div className="flex items-center space-x-2">
                  <span
                    className={`inline-block w-2 h-2 rounded-full ${guestPlayer.is_connected ? "bg-accent animate-pulse" : "bg-slate-600"
                      }`}
                    title={guestPlayer.is_connected ? "Connected" : "Disconnected"}
                  />
                  <Badge variant={guestPlayer.is_ready ? "accent" : "outline"}>
                    {guestPlayer.is_ready ? "Ready" : "Not Ready"}
                  </Badge>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-surface to-slate-800 border border-slate-700 flex items-center justify-center font-black text-base text-white shadow-inner">
                  {guestPlayer.username.substring(0, 2).toUpperCase()}
                </div>
                <div>
                  <div className="flex items-center space-x-1.5">
                    <span className="font-bold text-white text-base">
                      {guestPlayer.username}
                    </span>
                    {guestPlayer.user_id === currentUserId && (
                      <span className="text-[11px] text-accent font-semibold">(You)</span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-400">
                    {guestPlayer.is_connected ? "Connected" : "Offline"}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Waiting for Guest animation card */
            <div className="p-4 rounded-xl border-2 border-dashed border-slate-800/90 bg-slate-950/40 flex flex-col items-center justify-center text-center space-y-2 min-h-[110px]">
              <div className="flex items-center space-x-2 text-highlight text-sm font-semibold animate-pulse">
                <Sparkles className="w-4 h-4 text-highlight" />
                <span>Waiting for Guest...</span>
              </div>
              <p className="text-xs text-slate-500 max-w-xs">
                Share room code <span className="font-mono text-slate-300 font-bold">{room.room_code}</span> with your opponent.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="pt-2 border-t border-slate-800 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Ready Button */}
          {onReadyToggle && (
            <Button
              variant={me?.is_ready ? "secondary" : "primary"}
              className={`w-full py-3.5 font-bold text-sm flex items-center justify-center space-x-2 ${me?.is_ready
                ? "border-accent/40 text-accent hover:bg-accent/10"
                : "bg-accent hover:bg-accent-hover text-white shadow-lg shadow-accent/20"
                }`}
              onClick={onReadyToggle}
            >
              <Check className="w-4 h-4" />
              <span>{me?.is_ready ? "Cancel Ready" : "I'm Ready"}</span>
            </Button>
          )}

          {/* Start Game Button (Host Only) */}
          {isMeHost && (
            <Button
              variant="primary"
              disabled={!bothReady || isStarting}
              isLoading={isStarting}
              onClick={onStartGame}
              className={`w-full py-3.5 font-bold text-sm flex items-center justify-center space-x-2 ${bothReady
                ? "bg-highlight hover:bg-highlight-hover text-slate-950 shadow-lg shadow-highlight/25"
                : "bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed"
                }`}
            >
              <Play className="w-4 h-4" />
              <span>Start Match</span>
            </Button>
          )}

          {/* Guest waiting placeholder indicator when guest is ready */}
          {!isMeHost && (
            <div className="flex items-center justify-center px-4 py-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-400">
              {bothReady
                ? "Both players ready! Waiting for Host to start..."
                : "Waiting for both players to mark Ready..."}
            </div>
          )}
        </div>

        {/* Start Game Requirement Helper notice for Host */}
        {isMeHost && !bothReady && (
          <p className="text-center text-xs text-slate-400">
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
              className="text-xs text-red-400/80 hover:text-red-400 flex items-center space-x-1.5 py-1.5 px-3 rounded-lg hover:bg-red-500/10 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Leave Room</span>
            </button>
          </div>
        )}
      </div>
    </Card>
  );
};

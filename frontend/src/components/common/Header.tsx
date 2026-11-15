import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Trophy, Users, History, Settings as SettingsIcon, Radio, User } from "lucide-react";
import { useGame } from "../../contexts/GameContext";

export const Header: React.FC = () => {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const roomParam = searchParams.get("room");
  const { currentRoom, username } = useGame();

  const isRoomRoute = ["/lobby", "/draft", "/toss", "/live", "/scorecard"].some((path) =>
    location.pathname.startsWith(path)
  );

  const activeRoomCode = currentRoom?.room_code || (isRoomRoute ? roomParam : null);
  const isInActiveRoom = Boolean(isRoomRoute && activeRoomCode);

  const displayName = isInActiveRoom && username ? username : "Player";
  const avatarInitials = displayName === "Player" ? null : displayName.substring(0, 2).toUpperCase();

  const navLinks = [
    { label: "Lobby", path: "/lobby", icon: Users },
    { label: "Draft", path: "/draft", icon: Trophy },
    { label: "Live Match", path: "/live", icon: Radio },
    { label: "History", path: "/history", icon: History },
    { label: "Settings", path: "/settings", icon: SettingsIcon },
  ];

  return (
    <header className="sticky top-0 z-50 bg-background/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center space-x-2.5 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-accent to-emerald-400 flex items-center justify-center shadow-lg shadow-accent/25 group-hover:scale-105 transition-transform">
            <span className="font-black text-xl text-slate-950 font-serif tracking-tighter">XI</span>
          </div>
          <div>
            <span className="text-xl font-black tracking-tight text-white group-hover:text-accent transition-colors">
              Cric<span className="text-accent">XI</span>
            </span>
            <span className="hidden sm:inline-block ml-2 text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded bg-surface border border-slate-700 text-slate-400">
              T20 Draft
            </span>
          </div>
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center space-x-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-surface text-accent border border-slate-700"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/50"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User / Room Info */}
        <div className="flex items-center space-x-3">
          {isInActiveRoom && activeRoomCode && (
            <div className="flex items-center space-x-2 bg-surface px-3 py-1.5 rounded-lg border border-slate-700 text-xs">
              <span className="text-slate-400">Room:</span>
              <span className="font-mono font-bold text-highlight">{activeRoomCode}</span>
            </div>
          )}
          <div className="flex items-center space-x-2">
            <div
              className={`w-8 h-8 rounded-full border flex items-center justify-center text-xs font-bold uppercase ${
                avatarInitials
                  ? "bg-accent/20 border-accent/40 text-accent"
                  : "bg-slate-800 border-slate-700 text-slate-400"
              }`}
            >
              {avatarInitials ? avatarInitials : <User className="w-4 h-4 text-slate-400" />}
            </div>
            <span
              className={`hidden sm:inline-block text-sm font-medium ${
                displayName === "Player" ? "text-slate-400" : "text-slate-200"
              }`}
            >
              {displayName}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};


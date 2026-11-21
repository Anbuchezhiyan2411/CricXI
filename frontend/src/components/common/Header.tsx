import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Trophy, Users, History, Settings as SettingsIcon, User, BarChart3 } from "lucide-react";
import { useGame } from "../../contexts/GameContext";

export const Header: React.FC = () => {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const roomParam = searchParams.get("room");
  const { currentRoom, username } = useGame();

  const isRoomRoute = ["/lobby", "/draft", "/toss", "/scorecard"].some((path) =>
    location.pathname.startsWith(path)
  );

  const activeRoomCode = currentRoom?.room_code || (isRoomRoute ? roomParam : null);
  const isInActiveRoom = Boolean(isRoomRoute && activeRoomCode);

  const displayName = isInActiveRoom && username ? username : "Player";
  const avatarInitials = displayName === "Player" ? null : displayName.substring(0, 2).toUpperCase();

  const navLinks = [
    { label: "Lobby", path: "/lobby", icon: Users },
    { label: "Draft", path: "/draft", icon: Trophy },
    { label: "Analytics", path: "/analytics", icon: BarChart3 },
    { label: "History", path: "/history", icon: History },
    { label: "Settings", path: "/settings", icon: SettingsIcon },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#081826]/95 backdrop-blur-lg border-b border-[#1E3A5F]/70 shadow-lg shadow-black/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#0B3D91] via-[#1E3A5F] to-[#138A36] p-0.5 shadow-md shadow-[#0B3D91]/30 group-hover:scale-105 transition-transform">
            <div className="w-full h-full rounded-[10px] bg-[#081826] flex items-center justify-center">
              <span className="font-black text-lg text-[#F4C430] font-display tracking-tight">XI</span>
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="text-xl font-black tracking-tight text-white group-hover:text-[#F4C430] transition-colors font-display">
                Cric<span className="text-[#F4C430]">XI</span>
              </span>
              <span className="hidden sm:inline-block text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full bg-[#12263A] border border-[#1E3A5F] text-[#138A36]">
                Pro T20
              </span>
            </div>
          </div>
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center space-x-1.5">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition-all duration-200 ${
                  isActive
                    ? "bg-[#1E3A5F] text-[#F4C430] border border-[#F4C430]/30 shadow-md shadow-[#0B3D91]/20"
                    : "text-[#C7D2E2] hover:text-white hover:bg-[#12263A] hover:border hover:border-[#1E3A5F]/60"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? "text-[#F4C430]" : "text-[#C7D2E2]"}`} />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User / Room Info */}
        <div className="flex items-center space-x-3">
          {isInActiveRoom && activeRoomCode && (
            <div className="flex items-center space-x-2 bg-[#12263A] px-3.5 py-1.5 rounded-xl border border-[#1E3A5F] text-xs shadow-inner">
              <span className="w-2 h-2 rounded-full bg-[#138A36] animate-pulse" title="Connected" />
              <span className="text-[#C7D2E2] font-semibold text-[11px] uppercase tracking-wider">Room:</span>
              <span className="font-mono font-black text-[#F4C430] tracking-wider">{activeRoomCode}</span>
            </div>
          )}
          <div className="flex items-center space-x-2.5 bg-[#12263A]/80 border border-[#1E3A5F] px-3 py-1.5 rounded-xl">
            <div
              className={`w-7 h-7 rounded-lg border flex items-center justify-center text-xs font-black uppercase shadow-sm ${
                avatarInitials
                  ? "bg-gradient-to-tr from-[#0B3D91] to-[#1E3A5F] border-[#F4C430]/40 text-[#F4C430]"
                  : "bg-[#081826] border-[#1E3A5F] text-[#C7D2E2]"
              }`}
            >
              {avatarInitials ? avatarInitials : <User className="w-3.5 h-3.5 text-[#C7D2E2]" />}
            </div>
            <span
              className={`hidden sm:inline-block text-xs font-bold tracking-wide ${
                displayName === "Player" ? "text-[#C7D2E2]" : "text-white"
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


import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Trophy, Users, History, Settings as SettingsIcon, User, BarChart3, Menu, X } from "lucide-react";
import { useGame } from "../../contexts/GameContext";

export const Header: React.FC = () => {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const roomParam = searchParams.get("room");
  const { currentRoom, username } = useGame();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

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
        <Link to="/" className="flex items-center space-x-2.5 sm:space-x-3 group">
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-tr from-[#0B3D91] via-[#1E3A5F] to-[#138A36] p-0.5 shadow-md shadow-[#0B3D91]/30 group-hover:scale-105 transition-transform shrink-0">
            <div className="w-full h-full rounded-[10px] bg-[#081826] flex items-center justify-center">
              <span className="font-black text-base sm:text-lg text-[#F4C430] font-display tracking-tight">XI</span>
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="text-lg sm:text-xl font-black tracking-tight text-white group-hover:text-[#F4C430] transition-colors font-display">
                Cric<span className="text-[#F4C430]">XI</span>
              </span>
              <span className="text-[9px] sm:text-[10px] font-black uppercase tracking-widest px-1.5 sm:px-2 py-0.5 rounded-full bg-[#12263A] border border-[#1E3A5F] text-[#138A36]">
                Pro T20
              </span>
            </div>
          </div>
        </Link>

        {/* Desktop Navigation */}
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

        {/* User / Room Info & Mobile Hamburger */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {isInActiveRoom && activeRoomCode && (
            <div className="flex items-center space-x-1 sm:space-x-2 bg-[#12263A] px-2 sm:px-3 py-1.5 rounded-xl border border-[#1E3A5F] text-xs shadow-inner">
              <span className="w-2 h-2 rounded-full bg-[#138A36] animate-pulse" title="Connected" />
              <span className="hidden xs:inline text-[#C7D2E2] font-semibold text-[10px] sm:text-[11px] uppercase tracking-wider">Room:</span>
              <span className="font-mono font-black text-[#F4C430] tracking-wider text-xs">{activeRoomCode}</span>
            </div>
          )}
          <div className="flex items-center space-x-2 bg-[#12263A]/80 border border-[#1E3A5F] px-2 sm:px-3 py-1.5 rounded-xl">
            <div
              className={`w-6 h-6 sm:w-7 sm:h-7 rounded-lg border flex items-center justify-center text-xs font-black uppercase shadow-sm ${
                avatarInitials
                  ? "bg-gradient-to-tr from-[#0B3D91] to-[#1E3A5F] border-[#F4C430]/40 text-[#F4C430]"
                  : "bg-[#081826] border-[#1E3A5F] text-[#C7D2E2]"
              }`}
            >
              {avatarInitials ? avatarInitials : <User className="w-3.5 h-3.5 text-[#C7D2E2]" />}
            </div>
            <span
              className={`text-xs font-bold tracking-wide max-w-[80px] sm:max-w-none truncate ${
                displayName === "Player" ? "text-[#C7D2E2]" : "text-white"
              }`}
            >
              {displayName}
            </span>
          </div>

          {/* Mobile Menu Toggle Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            aria-label="Toggle navigation menu"
            className="md:hidden p-2 rounded-xl bg-[#12263A] border border-[#1E3A5F] text-[#C7D2E2] hover:text-[#F4C430] hover:border-[#F4C430]/40 transition-colors focus:outline-none"
          >
            {mobileMenuOpen ? <X className="w-5 h-5 text-[#F4C430]" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-[#1E3A5F]/80 bg-[#081826] px-4 py-3 space-y-1 shadow-2xl animate-in slide-in-from-top-2 duration-150">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center space-x-3 px-4 py-3 rounded-xl text-xs font-bold uppercase tracking-wider transition-all duration-150 ${
                  isActive
                    ? "bg-[#1E3A5F] text-[#F4C430] border border-[#F4C430]/40 shadow-md"
                    : "text-[#C7D2E2] hover:text-white hover:bg-[#12263A] border border-transparent"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-[#F4C430]" : "text-[#C7D2E2]"}`} />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
};


/**
 * Frontend Constants for CricXI.
 */

export const SUPPORTED_DECADES = [1980, 1990, 2000, 2010, 2020];

export const SUPPORTED_COUNTRIES = [
  "Afghanistan",
  "Australia",
  "Bangladesh",
  "England",
  "India",
  "New Zealand",
  "Pakistan",
  "South Africa",
  "Sri Lanka",
  "West Indies",
  "Zimbabwe",
];

export const ROLE_BADGE_COLORS: Record<string, string> = {
  BAT: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  WK: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  AR: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  PACE: "bg-red-500/20 text-red-400 border-red-500/30",
  SPIN: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
};

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const WS_BASE_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";


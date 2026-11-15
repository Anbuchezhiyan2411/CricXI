/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#0F172A", // primary dark slate
        surface: "#1E293B",    // slate-800
        surfaceLight: "#334155",
        accent: {
          DEFAULT: "#10B981",  // emerald-500
          hover: "#059669",    // emerald-600
          light: "#34D399",
        },
        highlight: {
          DEFAULT: "#F59E0B", // amber-500
          hover: "#D97706",   // amber-600
          light: "#FBBF24",
        },
        pitch: {
          dark: "#064E3B",
          light: "#047857",
        }
      },
    },
  },
  plugins: [],
}


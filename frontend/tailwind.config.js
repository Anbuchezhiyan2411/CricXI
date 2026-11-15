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
        // Commercial Cricket Design System
        cricket: {
          navy: "#081826",       // Deep background navy
          card: "#12263A",       // Elevation card surface
          hover: "#1E3A5F",      // Card hover / accent elevation
          primary: "#0B3D91",    // Deep royal blue
          secondary: "#138A36",  // Emerald grass green
          gold: "#F4C430",       // Championship gold
          red: "#E53935",        // Wicket / danger red
          subtext: "#C7D2E2",    // Legible secondary text
        },
        background: "#081826",   // primary dark navy
        surface: "#12263A",      // card surface
        surfaceLight: "#1E3A5F", // card hover / elevated
        accent: {
          DEFAULT: "#138A36",    // emerald green
          hover: "#0F6F2B",      // deep emerald
          light: "#2ECC71",
        },
        highlight: {
          DEFAULT: "#F4C430",    // trophy gold
          hover: "#D4A516",      // deep gold
          light: "#FDE047",
        },
        pitch: {
          dark: "#08331A",
          light: "#138A36",
        }
      },
      fontFamily: {
        sans: ['Inter', 'Manrope', 'system-ui', 'sans-serif'],
        display: ['Manrope', 'Outfit', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'button': '14px',
        'card': '18px',
        'dialog': '20px',
      },
      boxShadow: {
        'cricket-glow': '0 0 25px -5px rgba(11, 61, 145, 0.35)',
        'cricket-card': '0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3)',
        'cricket-gold': '0 0 20px -3px rgba(244, 196, 48, 0.3)',
      }
    },
  },
  plugins: [],
}


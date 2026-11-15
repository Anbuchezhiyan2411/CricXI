# CricXI Frontend

The CricXI client is a modern, responsive web application built with **React 19**, **TypeScript**, **Vite**, and **Tailwind CSS**.

---

## Design System

- **Primary Background**: `#0F172A` (Rich Dark Slate)
- **Surface**: `#1E293B` (Elevated Card Slate)
- **Accent**: `#10B981` (Emerald Green - Stadium Turf)
- **Highlight**: `#F59E0B` (Amber Gold - Trophy & Toss)
- **Typography**: Inter (Body) & Outfit (Display Headlines)

---

## Directory Structure

```
frontend/
├── public/                  # Static assets & cricket ball favicon
├── src/
│   ├── assets/              # SVGs, icons, illustrations
│   ├── components/
│   │   ├── common/          # Header, Footer, Card, Button, Badge, LoadingSpinner
│   │   ├── draft/           # Draft board & player pick components
│   │   ├── lobby/           # Multiplayer friend code lobby card
│   │   ├── match/           # Ball-by-ball commentary and live scoreboard
│   │   ├── scorecard/       # Official T20 match scorecard
│   │   └── toss/            # Toss ceremony visualization
│   ├── contexts/            # ThemeContext & GameContext
│   ├── hooks/               # usePlayers, useWebSocket
│   ├── layouts/             # RootLayout with persistent Header & Footer
│   ├── pages/               # LandingPage, CreateRoomPage, JoinRoomPage, LobbyPage, etc.
│   ├── routes/              # React Router v7 routes definition
│   ├── services/            # Axios API client, playerService, roomService
│   ├── types/               # TypeScript interfaces & types
│   ├── utils/               # Constants and helper utilities
│   ├── App.tsx              # Root component wrapped with providers
│   ├── index.css            # Tailwind directives and custom scrollbars
│   └── main.tsx             # React 19 entrypoint
├── package.json             # Dependencies and build scripts
├── vite.config.ts           # Vite proxy and path aliasing
└── tailwind.config.js       # CricXI theme colors and typography
```

---

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The application runs at `http://localhost:5173` with proxy pass-through to the FastAPI backend at `http://localhost:8000`.


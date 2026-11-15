# CricXI — Multiplayer T20 Cricket Draft & Simulation Platform

CricXI is a full-stack multiplayer cricket draft and realistic match simulation platform developed as an **Introduction to Data Science** project. Inspired by [500-0.com](https://500-0.com), CricXI elevates the experience with real-time two-player online rooms, decade-based draft pools, authentic batting position constraints, and stochastic T20 match simulations powered by official Cricsheet international cricket datasets.

---

## Game Overview

1. **Friend Code Matchmaking**: Two players connect using a 6-character room code.
2. **11-Round Era Draft**: Each round randomly draws one Country + Decade (e.g. *India 1990*, *Australia 2010*, *West Indies 1980*). Both players select one legend from that era's strongest historical Best XI.
3. **Locked Batting Positions**: Selected players must be placed into their historically authentic batting positions, locking that slot for the remainder of the draft.
4. **The Toss**: After building an XI with exactly one wicketkeeper and balanced bowling options, a toss is conducted where the winner elects to Bat or Bowl first.
5. **Realistic T20 Simulation**: The match is simulated ball-by-ball using real player statistical distributions (strike rates, dot ball percentages, economy rates, and wicket probabilities) with live commentary and complete scorecards.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, React Router DOM v7, Tailwind CSS, Framer Motion, Axios, Lucide React, Socket.IO Client |
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy ORM, SQLite, Pandas, Pydantic v2, WebSockets, Uvicorn |
| **Data Engine** | Official Cricsheet T20 International match data (506 players across 11 nations and 5 decades) |
| **Theme** | Dark slate `#0F172A` with emerald turf `#10B981` and amber trophy `#F59E0B` accents |

---

## Project Structure

```
CricXI/
│
├── backend/
│   ├── app/
│   │   ├── api/                 # REST routers (health, players, rooms, matches, history, ws)
│   │   ├── config/              # Application settings, constants, logging
│   │   ├── database/            # SQLAlchemy session and Base
│   │   ├── draft/               # Draft system interfaces (Phase 2)
│   │   ├── matchmaking/         # Lobby & room manager (Phase 2)
│   │   ├── models/              # SQLAlchemy models (Player, Room, DraftPick, Match)
│   │   ├── schemas/             # Pydantic v2 schemas
│   │   ├── services/            # DatasetLoader service
│   │   ├── simulation/          # T20 simulation engine (Phase 2)
│   │   ├── utils/               # Helper utilities
│   │   ├── websocket/           # WebSocket connection manager
│   │   └── main.py              # FastAPI application entrypoint
│   ├── requirements.txt         # Backend Python dependencies
│   ├── .env.example             # Backend environment template
│   └── README.md
│
├── frontend/
│   ├── public/                  # Static assets & icons
│   ├── src/
│   │   ├── components/          # Common UI, Lobby, Draft, Toss, Match, Scorecard
│   │   ├── contexts/            # ThemeContext & GameContext
│   │   ├── hooks/               # usePlayers, useWebSocket
│   │   ├── layouts/             # RootLayout with Header and Footer
│   │   ├── pages/               # LandingPage, CreateRoomPage, JoinRoomPage, LobbyPage, etc.
│   │   ├── routes/              # AppRoutes definition
│   │   ├── services/            # Axios API & Room services
│   │   ├── types/               # TypeScript interfaces
│   │   ├── utils/               # Constants and helper functions
│   │   ├── App.tsx              # Root component with providers
│   │   ├── index.css            # Tailwind directives and custom scrollbars
│   │   └── main.tsx             # React 19 entrypoint
│   ├── package.json             # Frontend dependencies
│   ├── vite.config.ts           # Vite configuration
│   ├── tailwind.config.js       # CricXI theme palette
│   └── README.md
│
├── Dataset/
│   ├── data/                    # Extracted Cricsheet T20I JSON files
│   ├── players/                 # players_<country>.csv files
│   ├── output/                  # master_players.csv, players.csv, player_decade_stats.csv
│   └── scripts/                 # Extraction, merge, rating, and cleaning scripts
│
├── docs/
│   └── architecture.md          # Architectural diagram & specification
│
├── .env.example
├── .gitignore
└── README.md
```

---

## Quickstart

### 1. Backend Setup

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Run FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Base URL: `http://localhost:8000`
- Interactive API Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/health`

### 2. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```

- Web Application: `http://localhost:5173`

---

## Project Roadmap

- [x] **Phase 1: Foundation & Clean Architecture**
  - [x] Master dataset curation (506 players, 11 nations, 5 decades)
  - [x] FastAPI REST endpoints & WebSocket connection manager
  - [x] SQLAlchemy ORM database models & SQLite integration
  - [x] React 19 + TypeScript frontend with routing, contexts, and dark stadium theme
  - [x] Architectural documentation and API schemas
- [ ] **Phase 2: Draft System & Match Simulation**
  - [ ] 11-round random Country + Decade draft algorithm
  - [ ] Authentic batting position locking validation
  - [ ] Coin toss animation and decision handler
  - [ ] Stochastic ball-by-ball T20 match simulation engine
  - [ ] Live commentary stream and calculated player scorecards
- [ ] **Phase 3: Production Hardening & Analytics**
  - [ ] Match history analytics & head-to-head win probability charts
  - [ ] Redis session persistence
  - [ ] Containerization (Docker Compose)


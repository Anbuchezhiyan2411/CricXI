# CricXI Backend Service

The CricXI backend is a high-performance Python 3.12+ / FastAPI application powering a multiplayer T20 cricket draft and match simulation game inspired by 500-0.com.

---

## Architecture Overview

```
backend/
├── app/
│   ├── api/                 # REST Routers & Dependency Injections
│   │   ├── routers/         # health, players, rooms, matches, history, websocket
│   │   └── deps.py          # FastDB session, DatasetService, WSManager dependencies
│   ├── config/              # Constants, settings, logging config
│   ├── database/            # SQLAlchemy Base & Session configuration
│   ├── draft/               # Draft system interfaces (Phase 2)
│   ├── matchmaking/         # Matchmaking logic (Phase 2)
│   ├── models/              # SQLAlchemy database models (Player, Room, DraftPick, Match)
│   ├── schemas/             # Pydantic validation schemas & request/response types
│   ├── services/            # DatasetLoader in-memory service
│   ├── simulation/          # Match simulation engine (Phase 2)
│   ├── utils/               # General helper utilities
│   ├── websocket/           # WebSocket ConnectionManager and RoomManager
│   └── main.py              # Application entrypoint & lifespan events
├── requirements.txt         # Pinned Python package dependencies
├── .env.example             # Template environment variables
└── README.md                # Backend service documentation
```

---

## Dataset Loading

The backend automatically loads the curated Cricsheet dataset (`app/data/master_players.csv`) on startup into memory via `DatasetLoader`.
The dataset contains 506 historically accurate players across 11 nations and 5 decades (1980s through 2020s), complete with comprehensive batting and bowling T20 statistics, strike rates, economy rates, and calculated ratings.

---

## Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service discovery & root info |
| `GET` | `/api/health` | Health status and dataset load diagnostics |
| `GET` | `/api/players` | Paginated player list with filters (country, decade, role, search) |
| `GET` | `/api/players/meta/filters` | Filter metadata (countries, decades, roles) |
| `GET` | `/api/players/{id}` | Single player profile by ID |
| `GET` | `/api/players/country/{c}/decade/{d}` | Best XI candidates for draft rounds |
| `POST` | `/api/rooms` | Create new multiplayer room |
| `POST` | `/api/rooms/join` | Join existing room by code |
| `GET` | `/api/rooms/{code}` | Retrieve room status and player list |
| `GET` | `/api/matches/{id}` | Match details and scorecard |
| `GET` | `/api/history` | Paginated match history |
| `WS` | `/ws/{room_code}/{player_id}` | Real-time WebSocket connection |

---

## Running the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation is available at `http://localhost:8000/docs`.


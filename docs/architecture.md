# CricXI System Architecture & Design Specification

## 1. System Overview

CricXI is an online multiplayer cricket draft and realistic T20 simulation platform built as an Introduction to Data Science project. Inspired by the draft mechanics of 500-0.com, CricXI introduces two-player online rooms, decade-based draft pools, authentic historical batting positions, real player metrics extracted from Cricsheet T20 international datasets, and an upcoming stochastic ball-by-ball simulation engine.

---

## 2. High-Level Architecture

```mermaid
graph TD
    subgraph Frontend ["Client Tier (React 19 + TypeScript)"]
        UI["UI Layer (Tailwind CSS + Lucide)"]
        Router["React Router v7"]
        State["GameContext + ThemeContext"]
        NetClient["Axios REST + WebSocket Client"]
    end

    subgraph Backend ["Server Tier (FastAPI + Python 3.12+)"]
        API["REST API Endpoints (/api/...)"]
        WSHandler["WebSocket Manager (/ws/...)"]
        DataLoader["DatasetLoader (In-Memory Pandas)"]
        DBLayer["SQLAlchemy ORM + SQLite"]
    end

    subgraph DataTier ["Data Tier"]
        MasterCSV["master_players.csv (506 players)"]
        Database["cricxi.db (SQLite)"]
    end

    UI --> Router
    Router --> State
    State --> NetClient
    NetClient -->|HTTP REST| API
    NetClient -->|Bidirectional WS| WSHandler
    API --> DataLoader
    API --> DBLayer
    DataLoader --> MasterCSV
    DBLayer --> Database
```

---

## 3. Data Flow & Domain Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Player1 as Host (Player 1)
    actor Player2 as Challenger (Player 2)
    participant Client as CricXI Frontend
    participant Server as CricXI Backend
    participant Dataset as Cricsheet Dataset

    Player1->>Client: Click "Create Room"
    Client->>Server: POST /api/rooms { username: "Host" }
    Server-->>Client: 201 Created { room_code: "8K2M9P" }
    Player1->>Player2: Share Code "8K2M9P"
    Player2->>Client: Enter Code & Join
    Client->>Server: POST /api/rooms/join { room_code: "8K2M9P" }
    Server-->>Client: 200 OK (Room full)
    Client->>Server: WS Connect /ws/8K2M9P/{player_id}
    Server-->>Client: Broadcast: PLAYER_CONNECTED

    note over Client,Server: Phase 2: 11-Round Draft & Simulation
    loop 11 Draft Rounds
        Server->>Dataset: Sample Country + Decade (e.g. India 1990)
        Server-->>Client: Present 11 Best Candidates
        Player1->>Server: Pick Player & Batting Position
        Player2->>Server: Pick Player & Batting Position
    end
    Server->>Server: Conduct Toss (Bat/Bowl)
    Server->>Server: Run T20 Simulation Engine
    Server-->>Client: Stream Ball-by-Ball Events & Scorecard
```

---

## 4. Database Schema (SQLAlchemy Models)

### `players` Table
- `id` (Integer, Primary Key)
- `player_id` (Integer, Indexed)
- `player_name` (String, Indexed)
- `country` (String, Indexed)
- `decade` (Integer, Indexed)
- `batting_hand`, `bowling_hand`, `bowling_type`, `primary_role`, `eligible_positions`
- `is_captain`, `is_wicketkeeper`
- Batting statistics: `matches`, `innings`, `runs`, `strike_rate`, `batting_average`, `fifties`, `hundreds`, `sixes`, `fours`, `dot_ball_percentage`
- Bowling statistics: `wickets`, `balls_bowled`, `economy`, `bowling_average`, `maidens`, `four_wickets`, `five_wickets`
- Calculated ratings: `batting_rating`, `bowling_rating`, `overall_rating`

### `rooms` Table
- `id` (Integer, Primary Key)
- `room_code` (String(8), Unique, Indexed)
- `host_id` (String(100))
- `status` (Enum: WAITING, DRAFTING, TOSS, LIVE, COMPLETED, ABANDONED)
- `current_round` (Integer, Default: 1)
- `created_at`, `updated_at` (DateTime)

### `room_players` Table
- `id` (Integer, Primary Key)
- `room_id` (Foreign Key -> rooms.id)
- `user_id` (String(100), Indexed)
- `username` (String(50))
- `is_host` (Boolean)
- `is_ready` (Boolean)
- `joined_at` (DateTime)

### `draft_picks` Table
- `id` (Integer, Primary Key)
- `room_id` (Foreign Key -> rooms.id)
- `round_number` (Integer)
- `user_id` (String(100))
- `player_id` (Integer)
- `player_name` (String(100))
- `batting_position` (Integer, 1-11)
- `selected_country` (String(50))
- `selected_decade` (Integer)

### `matches` Table
- `id` (Integer, Primary Key)
- `room_id` (Foreign Key -> rooms.id)
- `team1_user_id`, `team2_user_id` (String(100))
- `toss_winner_id`, `toss_decision` (String)
- `status` (Enum: PENDING, IN_PROGRESS, FIRST_INNINGS, INNINGS_BREAK, SECOND_INNINGS, COMPLETED)
- `winner_user_id`, `result_margin` (String)

### `match_innings` & `ball_events` Tables
- Store granular ball-by-ball outputs for replay, live commentary streaming, and post-match scorecard calculation.

---

## 5. Security & Constraints
- Sandbox and environment independence.
- No client-side score computation: The server acts as the single source of truth for all drafting outcomes and match simulation logic.
- Input validation via Pydantic v2 schemas across all REST endpoints and WebSocket payloads.


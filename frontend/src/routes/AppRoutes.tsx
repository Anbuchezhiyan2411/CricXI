import React from "react";
import { Routes, Route } from "react-router-dom";
import { RootLayout } from "../layouts/RootLayout";
import { LandingPage } from "../pages/LandingPage";
import { CreateRoomPage } from "../pages/CreateRoomPage";
import { JoinRoomPage } from "../pages/JoinRoomPage";
import { LobbyPage } from "../pages/LobbyPage";
import { DraftPage } from "../pages/DraftPage";
import { TossPage } from "../pages/TossPage";
import { LiveMatchPage } from "../pages/LiveMatchPage";
import { ScorecardPage } from "../pages/ScorecardPage";
import { MatchHistoryPage } from "../pages/MatchHistoryPage";
import { SettingsPage } from "../pages/SettingsPage";
import { NotFoundPage } from "../pages/NotFoundPage";

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<RootLayout />}>
        <Route index element={<LandingPage />} />
        <Route path="create-room" element={<CreateRoomPage />} />
        <Route path="join-room" element={<JoinRoomPage />} />
        <Route path="lobby" element={<LobbyPage />} />
        <Route path="draft" element={<DraftPage />} />
        <Route path="toss" element={<TossPage />} />
        <Route path="live" element={<LiveMatchPage />} />
        <Route path="scorecard" element={<ScorecardPage />} />
        <Route path="history" element={<MatchHistoryPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
};


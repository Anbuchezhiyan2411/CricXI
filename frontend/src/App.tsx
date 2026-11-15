import React from "react";
import { BrowserRouter } from "react-router-dom";
import { ThemeProvider } from "./contexts/ThemeContext";
import { GameProvider } from "./contexts/GameContext";
import { ToastProvider } from "./components/common/Toast";
import { AppRoutes } from "./routes/AppRoutes";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <GameProvider>
          <ToastProvider>
            <AppRoutes />
          </ToastProvider>
        </GameProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
};

export default App;

import React from "react";
import { Settings as SettingsIcon, Sun, Moon } from "lucide-react";
import { Card } from "../components/common/Card";
import { Button } from "../components/common/Button";
import { useTheme } from "../contexts/ThemeContext";

export const SettingsPage: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-6">
      <div className="flex items-center space-x-3 pb-2 border-b border-slate-800">
        <SettingsIcon className="w-8 h-8 text-accent" />
        <div>
          <h1 className="text-2xl font-bold text-white">Application Settings</h1>
          <p className="text-xs text-slate-400">Configure theme, display, and backend connection preferences.</p>
        </div>
      </div>

      <Card className="space-y-4">
        <h3 className="font-bold text-slate-200 text-sm">Theme Appearance</h3>
        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900 border border-slate-800">
          <div className="flex items-center space-x-3">
            {theme === "dark" ? <Moon className="w-5 h-5 text-accent" /> : <Sun className="w-5 h-5 text-amber-400" />}
            <div>
              <div className="text-sm font-semibold text-slate-200">Current Theme</div>
              <div className="text-xs text-slate-400 capitalize">{theme} Mode</div>
            </div>
          </div>
          <Button variant="secondary" size="sm" onClick={toggleTheme}>
            Toggle Theme
          </Button>
        </div>
      </Card>

      <Card className="space-y-4">
        <h3 className="font-bold text-slate-200 text-sm">Dataset & Server Connectivity</h3>
        <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Backend API URL:</span>
            <span className="font-mono text-slate-300">http://localhost:8000</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">WebSocket Endpoint:</span>
            <span className="font-mono text-slate-300">ws://localhost:8000</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Database Engine:</span>
            <span className="font-mono text-slate-300">SQLite (cricxi.db)</span>
          </div>
        </div>
      </Card>
    </div>
  );
};


import type { TradeAction } from "@/lib/types";

export const CHART_PERIODS = [
  { value: "1W", label: "1W" },
  { value: "1M", label: "1M" },
  { value: "3M", label: "3M" },
  { value: "ALL", label: "All" },
] as const;

export const CHART_COLORS = {
  primary: "#3b82f6", // Matches globals.css --primary electric blue 
  green: "#10b981",   // Matches globals.css --profit
  red: "#ef4444",     // Matches globals.css --loss
} as const;

export const ACTION_COLORS: Record<TradeAction, string> = {
  BUY: "border-profit/30 bg-profit/10 text-profit",
  SELL: "border-loss/30 bg-loss/10 text-loss",
  HOLD: "border-warning/30 bg-warning/10 text-warning",
};

export const MODEL_TYPES: Record<string, string> = {
  lstm: "LSTM",
  xgboost: "XGBoost",
};

export const ROLE_BADGES: Record<string, string> = {
  admin: "border-primary/30 bg-primary/10 text-primary",
  user: "border-secondary bg-secondary/40 text-foreground",
};

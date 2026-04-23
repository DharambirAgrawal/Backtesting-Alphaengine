"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, X, RefreshCw } from "lucide-react";

/**
 * ConnectionBanner
 *
 * Renders a dismissible banner when the backend is unreachable.
 * Render free-tier instances cold-start in ~20-40s; this banner
 * prevents users from thinking the app is broken.
 *
 * Usage: Mount once in DashboardLayout. The banner monitors
 * window fetch events via a custom event dispatched from lib/api.ts
 * (or can be shown manually via the exported helper).
 */

// Custom event key — dispatched from api.ts on first 503 / network error
const BACKEND_DOWN_EVENT = "alpha:backend-down";
const BACKEND_UP_EVENT = "alpha:backend-up";

export function dispatchBackendDown() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(BACKEND_DOWN_EVENT));
  }
}

export function dispatchBackendUp() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(BACKEND_UP_EVENT));
  }
}

export function ConnectionBanner() {
  const [visible, setVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const handleDown = () => {
      if (!dismissed) setVisible(true);
    };
    const handleUp = () => {
      setVisible(false);
      setElapsed(0);
    };

    window.addEventListener(BACKEND_DOWN_EVENT, handleDown);
    window.addEventListener(BACKEND_UP_EVENT, handleUp);
    return () => {
      window.removeEventListener(BACKEND_DOWN_EVENT, handleDown);
      window.removeEventListener(BACKEND_UP_EVENT, handleUp);
    };
  }, [dismissed]);

  // Elapsed second counter while banner is visible
  useEffect(() => {
    if (!visible) {
      setElapsed(0);
      return;
    }
    const interval = setInterval(() => {
      setElapsed((s) => s + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="connection-banner flex items-center gap-3 bg-warning/10 border-b border-warning/30 px-4 py-2.5 text-sm">
      <AlertTriangle className="h-4 w-4 text-warning shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="text-warning font-medium">Backend is starting up</span>
        <span className="text-warning/70 ml-2">
          — Render free tier takes ~20–40s to wake.
          {elapsed > 0 && ` (${elapsed}s)`}
        </span>
      </div>
      <button
        onClick={() => window.location.reload()}
        className="flex items-center gap-1.5 text-xs text-warning/70 hover:text-warning transition-colors shrink-0"
        title="Reload page"
      >
        <RefreshCw className="h-3 w-3" />
        Retry
      </button>
      <button
        onClick={() => {
          setDismissed(true);
          setVisible(false);
        }}
        className="text-warning/50 hover:text-warning transition-colors shrink-0"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

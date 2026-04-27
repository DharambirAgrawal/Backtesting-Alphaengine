"use client";

import { cn } from "@/lib/utils";
import { useCountdown } from "@/hooks/use-dashboard";
import { Play, Pause, Loader2 } from "lucide-react";

interface AgentStatusBadgeProps {
  status: "active" | "paused" | "running";
  nextRun?: string | null;
  timezoneLabel?: string;
  className?: string;
}

export function AgentStatusBadge({
  status,
  nextRun,
  timezoneLabel = "ET",
  className,
}: AgentStatusBadgeProps) {
  const countdown = useCountdown(status === "active" ? nextRun || null : null);

  return (
    <div
      className={cn(
        "flex max-w-full items-center gap-2 rounded-full px-3 py-1.5 text-sm",
        status === "active" && "bg-profit/10 text-profit",
        status === "paused" && "bg-muted text-muted-foreground",
        status === "running" && "bg-primary/10 text-primary",
        className
      )}
    >
      {status === "active" && (
        <>
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-profit opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-profit" />
          </span>
          <span className="truncate">
            Next run in {countdown || "..."} ({timezoneLabel})
          </span>
        </>
      )}
      {status === "paused" && (
        <>
          <Pause className="h-3 w-3" />
          <span>Paused</span>
        </>
      )}
      {status === "running" && (
        <>
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Agent running...</span>
        </>
      )}
    </div>
  );
}

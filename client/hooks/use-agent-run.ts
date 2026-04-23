"use client";

import useSWR from "swr";
import { useState, useCallback, useRef, useEffect } from "react";
import {
  triggerAgentRun,
  getAgentRuns,
  pauseAgent,
  resumeAgent,
} from "@/lib/api";
import type { AgentRun } from "@/lib/types";

export function useAgentRun(portfolioId: string | null) {
  const [isTriggering, setIsTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data, mutate } = useSWR<AgentRun[]>(
    portfolioId ? `agent-runs-${portfolioId}` : null,
    () => getAgentRuns(portfolioId as string),
    {
      revalidateOnFocus: false,
      // Whenever the latest run is "running", poll SWR every 2 seconds to check status
      refreshInterval: (data) => {
        if (!data || data.length === 0) return 0;
        return data[0].status === "running" ? 2000 : 0;
      },
    }
  );

  // Get the most recent run
  const latestRun = data?.[0];

  const run = useCallback(async () => {
    if (!portfolioId) return;

    setIsTriggering(true);
    setError(null);

    try {
      const runData = await triggerAgentRun(portfolioId);
      // Immediately mutate local cache to show as running, SWR will take over polling
      await mutate();
      return runData;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run agent");
      throw err;
    } finally {
      setIsTriggering(false);
    }
  }, [portfolioId, mutate]);

  const pause = useCallback(async () => {
    if (!portfolioId) return;

    try {
      await pauseAgent(portfolioId);
      mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to pause agent");
      throw err;
    }
  }, [portfolioId, mutate]);

  const resume = useCallback(async () => {
    if (!portfolioId) return;

    try {
      await resumeAgent(portfolioId);
      mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resume agent");
      throw err;
    }
  }, [portfolioId, mutate]);

  return {
    runs: data ?? [],
    latestRun,
    isRunning: isTriggering || latestRun?.status === "running",
    error,
    run,
    pause,
    resume,
    refresh: mutate,
  };
}

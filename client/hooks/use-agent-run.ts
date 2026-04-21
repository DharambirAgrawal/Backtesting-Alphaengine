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
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const { data, mutate } = useSWR<AgentRun[]>(
    portfolioId ? `agent-runs-${portfolioId}` : null,
    () => getAgentRuns(portfolioId as string),
    {
      revalidateOnFocus: false,
    }
  );

  // Get the most recent run
  const latestRun = data?.[0];

  // Clear polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const run = useCallback(async () => {
    if (!portfolioId) return;

    setIsRunning(true);
    setError(null);

    try {
      const runData = await triggerAgentRun(portfolioId);

      // Start polling for completion
      pollIntervalRef.current = setInterval(async () => {
        const runs = await getAgentRuns(portfolioId);
        const currentRun = runs.find((r) => r.id === runData.id);

        if (currentRun?.status === "done" || currentRun?.status === "failed") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          setIsRunning(false);
          mutate();
        }
      }, 3000);

      return runData;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run agent");
      setIsRunning(false);
      throw err;
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
    isRunning: isRunning || latestRun?.status === "running",
    error,
    run,
    pause,
    resume,
    refresh: mutate,
  };
}

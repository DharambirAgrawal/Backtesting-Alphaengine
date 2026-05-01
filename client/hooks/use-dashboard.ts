"use client";

import useSWR from "swr";
import { getDashboard, getChartData } from "@/lib/api";
import type { DashboardData, ChartData } from "@/lib/types";
import { useState, useEffect } from "react";

export function useDashboard(portfolioId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<DashboardData>(
    portfolioId ? `dashboard-${portfolioId}` : null,
    () => getDashboard(portfolioId as string),
    {
      revalidateOnFocus: false,
      refreshInterval: 60000, // Poll every 60s when tab is visible
      refreshWhenHidden: false,
      dedupingInterval: 10000, // Increased from 5s to 10s to prevent duplicate requests
    }
  );

  return {
    dashboard: data,
    isLoading,
    error,
    refresh: mutate,
  };
}

export function useChartData(
  portfolioId: string | null,
  period: string = "1M"
) {
  const { data, error, isLoading, mutate } = useSWR<ChartData>(
    portfolioId ? `chart-${portfolioId}-${period}` : null,
    () => getChartData(portfolioId as string, period),
    {
      revalidateOnFocus: false,
      keepPreviousData: true,
      dedupingInterval: 10000, // Increased from 5s to 10s
    }
  );

  return {
    chartData: data,
    isLoading,
    error,
    refresh: mutate,
  };
}

// Hook for countdown to next run
export function useCountdown(targetDate: string | null) {
  const [timeLeft, setTimeLeft] = useState<string>("");

  useEffect(() => {
    if (!targetDate) {
      setTimeLeft("");
      return;
    }

    const calculateTimeLeft = () => {
      const now = new Date();
      const target = new Date(targetDate);
      const diff = target.getTime() - now.getTime();

      if (diff <= 0) {
        return "Now";
      }

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      if (hours > 0) {
        return `${hours}h ${minutes}m`;
      }
      if (minutes > 0) {
        return `${minutes}m ${seconds}s`;
      }
      return `${seconds}s`;
    };

    setTimeLeft(calculateTimeLeft());

    const interval = setInterval(() => {
      setTimeLeft(calculateTimeLeft());
    }, 1000);

    return () => clearInterval(interval);
  }, [targetDate]);

  return timeLeft;
}

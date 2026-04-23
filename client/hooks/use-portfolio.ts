"use client";

import useSWR from "swr";
import { getPortfolios, getPortfolio } from "@/lib/api";
import type { Portfolio } from "@/lib/types";

export function usePortfolios(enabled = true) {
  const { data, error, isLoading, mutate } = useSWR<Portfolio[]>(
    enabled ? "portfolios" : null,
    getPortfolios,
    {
      revalidateOnFocus: false,
    }
  );

  return {
    portfolios: data ?? [],
    isLoading,
    error,
    refresh: mutate,
  };
}

export function usePortfolio(id: string | null) {
  const { data, error, isLoading, mutate } = useSWR<Portfolio>(
    id ? `portfolio-${id}` : null,
    () => getPortfolio(id as string),
    {
      revalidateOnFocus: false,
    }
  );

  return {
    portfolio: data,
    isLoading,
    error,
    refresh: mutate,
  };
}

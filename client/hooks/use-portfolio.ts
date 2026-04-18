"use client";

import useSWR from "swr";
import { getPortfolios, getPortfolio } from "@/lib/api";
import type { Portfolio } from "@/lib/types";

export function usePortfolios() {
  const { data, error, isLoading, mutate } = useSWR<Portfolio[]>(
    "portfolios",
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
    () => (id ? getPortfolio(id) : null),
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

"use client";

import useSWR from "swr";
import { getTransactions } from "@/lib/api";
import type { PaginatedTransactions, TransactionFilters } from "@/lib/types";
import { useState, useCallback } from "react";

export function useTransactions(
  portfolioId: string | null,
  initialFilters: TransactionFilters = {}
) {
  const [filters, setFilters] = useState<TransactionFilters>({
    limit: 20,
    offset: 0,
    ...initialFilters,
  });

  const { data, error, isLoading, mutate } = useSWR<PaginatedTransactions>(
    portfolioId
      ? `transactions-${portfolioId}-${JSON.stringify(filters)}`
      : null,
    () => (portfolioId ? getTransactions(portfolioId, filters) : null),
    {
      revalidateOnFocus: false,
    }
  );

  const updateFilters = useCallback((newFilters: Partial<TransactionFilters>) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      offset: newFilters.offset ?? 0, // Reset offset when filters change
    }));
  }, []);

  const nextPage = useCallback(() => {
    if (data && (filters.offset ?? 0) + (filters.limit ?? 20) < data.total) {
      setFilters((prev) => ({
        ...prev,
        offset: (prev.offset ?? 0) + (prev.limit ?? 20),
      }));
    }
  }, [data, filters]);

  const prevPage = useCallback(() => {
    setFilters((prev) => ({
      ...prev,
      offset: Math.max(0, (prev.offset ?? 0) - (prev.limit ?? 20)),
    }));
  }, []);

  const goToPage = useCallback((page: number) => {
    setFilters((prev) => ({
      ...prev,
      offset: page * (prev.limit ?? 20),
    }));
  }, []);

  const currentPage = Math.floor((filters.offset ?? 0) / (filters.limit ?? 20));
  const totalPages = data ? Math.ceil(data.total / (filters.limit ?? 20)) : 0;

  return {
    transactions: data?.transactions ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    filters,
    updateFilters,
    nextPage,
    prevPage,
    goToPage,
    currentPage,
    totalPages,
    refresh: mutate,
  };
}

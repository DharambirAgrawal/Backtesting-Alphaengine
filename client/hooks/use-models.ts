"use client";

import useSWR from "swr";
import { useState, useCallback } from "react";
import {
  getModels,
  getModelsOverview,
  trainTicker,
  retrainAll,
  getModelAccuracy,
} from "@/lib/api";
import type { MLModel, ModelsOverview } from "@/lib/types";

interface UseModelsOptions {
  portfolioId?: string;
  trackedTickers?: string[];
  enabled?: boolean;
}

export function useModels(options: UseModelsOptions = {}) {
  const [retrainingTickers, setRetrainingTickers] = useState<Set<string>>(
    new Set()
  );
  const { portfolioId, trackedTickers, enabled = true } = options;

  const { data, error, isLoading, mutate } = useSWR<MLModel[]>(
    enabled ? (portfolioId ? `models-${portfolioId}` : "models") : null,
    () => getModels({ portfolioId }),
    {
      revalidateOnFocus: false,
    }
  );

  /**
   * Trigger retraining of both LSTM + XGBoost for a ticker.
   * Backend endpoint: POST /models/train/{ticker}
   */
  const retrain = useCallback(
    async (ticker: string) => {
      setRetrainingTickers((prev) => new Set(prev).add(ticker));

      try {
        await trainTicker(ticker);

        // Poll every 3s up to 90s, check if trained_at updated
        const originalTrainedAt = data
          ?.filter((m) => m.ticker === ticker)
          .map((m) => m.trained_at);

        let elapsed = 0;
        const poll = setInterval(async () => {
          elapsed += 3000;
          try {
            const latest = await getModels({ portfolioId });
            const tickerModels = latest.filter((m) => m.ticker === ticker);
            const updated = tickerModels.some(
              (m, idx) =>
                !originalTrainedAt ||
                m.trained_at !== originalTrainedAt[idx]
            );

            if (updated || elapsed >= 90000) {
              clearInterval(poll);
              setRetrainingTickers((prev) => {
                const next = new Set(prev);
                next.delete(ticker);
                return next;
              });
              mutate();
            }
          } catch {
            // keep polling until timeout
          }
        }, 3000);
      } catch (error) {
        setRetrainingTickers((prev) => {
          const next = new Set(prev);
          next.delete(ticker);
          return next;
        });
        throw error;
      }
    },
    [data, mutate, portfolioId]
  );

  /**
   * Retrain every active model in the portfolio.
   * Backend endpoint: POST /models/retrain-all
   */
  const retrainAllModels = useCallback(async () => {
    const tickers = Array.from(
      new Set(
        (trackedTickers && trackedTickers.length > 0
          ? trackedTickers
          : (data ?? []).map((model) => model.ticker)
        ).map((ticker) => ticker.toUpperCase())
      )
    );
    setRetrainingTickers(new Set(tickers));

    try {
      await retrainAll(portfolioId);

      // Poll every 5s up to 180s for refresh
      let elapsed = 0;
      const poll = setInterval(async () => {
        elapsed += 5000;
        await mutate();
        if (elapsed >= 180000) {
          clearInterval(poll);
          setRetrainingTickers(new Set());
        }
      }, 5000);
    } catch (error) {
      setRetrainingTickers(new Set());
      throw error;
    }
  }, [data, mutate, portfolioId, trackedTickers]);

  const isRetraining = useCallback(
    (ticker: string) => retrainingTickers.has(ticker),
    [retrainingTickers]
  );

  return {
    models: data ?? [],
    isLoading,
    error,
    retrain,
    retrainAllModels,
    isRetraining,
    isAnyRetraining: retrainingTickers.size > 0,
    refresh: mutate,
  };
}

export function useModelsOverview(portfolioId?: string) {
  const { data, error, isLoading, mutate } = useSWR<ModelsOverview>(
    portfolioId ? `models-overview-${portfolioId}` : "models-overview",
    () => getModelsOverview(portfolioId),
    {
      revalidateOnFocus: false,
    }
  );

  return {
    overview: data,
    isLoading,
    error,
    refresh: mutate,
  };
}

/**
 * Fetches accuracy history for a specific ticker (+ optional model type).
 * Backend endpoint: GET /models/{ticker}/accuracy?model_type=lstm
 */
export function useModelAccuracy(
  ticker: string | null,
  modelType: string | null
) {
  const { data, error, isLoading } = useSWR(
    ticker ? `accuracy-${ticker}-${modelType ?? "all"}` : null,
    () =>
      ticker ? getModelAccuracy(ticker, modelType ?? undefined) : null,
    {
      revalidateOnFocus: false,
    }
  );

  return {
    accuracy: data,
    isLoading,
    error,
  };
}

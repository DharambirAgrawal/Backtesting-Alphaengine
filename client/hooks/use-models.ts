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
import type { MLModel, ModelRetrainAllResult, ModelsOverview } from "@/lib/types";

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
        await mutate();
        setRetrainingTickers((prev) => {
          const next = new Set(prev);
          next.delete(ticker);
          return next;
        });
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
  const retrainAllModels = useCallback(async (): Promise<ModelRetrainAllResult> => {
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
      const result = await retrainAll(portfolioId);
      await mutate();
      setRetrainingTickers(new Set());
      return result;
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

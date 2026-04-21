"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription } from "@/components/ui/empty";
import { ModelCard } from "@/components/models/model-card";
import { AccuracyChart } from "@/components/models/accuracy-chart";
import { useModels } from "@/hooks/use-models";
import { usePortfolio } from "@/hooks/use-portfolio";
import { toast } from "sonner";
import { Brain, RefreshCw } from "lucide-react";

export default function ModelsPage() {
  const params = useParams();
  const portfolioId = params.portfolioId as string;

  const { portfolio } = usePortfolio(portfolioId);
  const {
    models,
    isLoading,
    retrain,
    retrainAllModels,
    isRetraining,
    isAnyRetraining,
  } = useModels({
    portfolioId,
    trackedTickers: portfolio?.tickers ?? [],
  });

  const [accuracyView, setAccuracyView] = useState<{
    ticker: string;
    modelType: string;
  } | null>(null);

  // Retraining one ticker trains BOTH model types on the backend
  const handleRetrain = async (ticker: string) => {
    try {
      await retrain(ticker);
      toast.success(`Retraining ${ticker}`, {
        description: "Training both LSTM and XGBoost models.",
      });
    } catch {
      toast.error("Failed to start retraining");
    }
  };

  const handleRetrainAll = async () => {
    try {
      await retrainAllModels();
      toast.success("Retraining all models", {
        description: "This may take a minute or two.",
      });
    } catch {
      toast.error("Failed to start retraining");
    }
  };

  return (
    <DashboardLayout portfolioId={portfolioId}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Trained Models
            </h1>
            <p className="text-muted-foreground">
              ML models used for price prediction and trading decisions
            </p>
          </div>
          <Button
            onClick={handleRetrainAll}
            disabled={isAnyRetraining || !portfolio?.tickers.length}
          >
            {isAnyRetraining ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Retraining...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" />
                Retrain All
              </>
            )}
          </Button>
        </div>

        {isLoading || !portfolio ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-64" />
            ))}
          </div>
        ) : portfolio.tickers.length === 0 ? (
          <Empty>
            <EmptyHeader>
              <Brain className="h-8 w-8 text-muted-foreground" />
              <EmptyTitle>No tickers configured</EmptyTitle>
              <EmptyDescription>
                Add at least one ticker in portfolio settings to start training
                models.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : models.length === 0 ? (
          <Empty>
            <EmptyHeader>
              <Brain className="h-8 w-8 text-muted-foreground" />
              <EmptyTitle>No models trained yet</EmptyTitle>
              <EmptyDescription>
                Models are still training or have not been generated for these
                tickers yet. You can retry training from here.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {models.map((model) => (
              <ModelCard
                key={model.id}
                model={model}
                isRetraining={isRetraining(model.ticker)}
                onRetrain={() => handleRetrain(model.ticker)}
                onViewAccuracy={() =>
                  setAccuracyView({
                    ticker: model.ticker,
                    modelType: model.model_type,
                  })
                }
              />
            ))}
          </div>
        )}
      </div>

      <AccuracyChart
        ticker={accuracyView?.ticker ?? null}
        modelType={accuracyView?.modelType ?? null}
        open={!!accuracyView}
        onClose={() => setAccuracyView(null)}
      />
    </DashboardLayout>
  );
}

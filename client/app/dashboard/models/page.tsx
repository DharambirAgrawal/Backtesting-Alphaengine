"use client";

import Link from "next/link";
import { useState, type ComponentType } from "react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { AccuracyChart } from "@/components/models/accuracy-chart";
import { ModelCard } from "@/components/models/model-card";
import { RelativeDate } from "@/components/ui/relative-date";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useModels, useModelsOverview } from "@/hooks/use-models";
import { MODEL_TYPES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import {
  Activity,
  Brain,
  Layers3,
  RefreshCw,
  Sparkles,
  Workflow,
} from "lucide-react";
import { toast } from "sonner";

export default function GlobalModelsPage() {
  const {
    overview,
    isLoading: isOverviewLoading,
    refresh: refreshOverview,
  } = useModelsOverview();
  const trackedTickers = overview?.coverage.map((item) => item.ticker) ?? [];
  const {
    models,
    isLoading: isModelsLoading,
    retrain,
    retrainAllModels,
    isRetraining,
    isAnyRetraining,
    refresh: refreshModels,
  } = useModels({ trackedTickers });

  const [accuracyView, setAccuracyView] = useState<{
    ticker: string;
    modelType: string;
  } | null>(null);
  const [lastRetrainFailures, setLastRetrainFailures] = useState<
    Record<string, string>
  >({});

  const handleRetrain = async (ticker: string) => {
    try {
      await retrain(ticker);
      await refreshOverview();
      setLastRetrainFailures((prev) => {
        const next = { ...prev };
        delete next[ticker.toUpperCase()];
        return next;
      });
      toast.success(`Retraining ${ticker}`, {
        description: "Refreshing both LSTM and XGBoost models.",
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Please try again.";
      setLastRetrainFailures((prev) => ({
        ...prev,
        [ticker.toUpperCase()]: message,
      }));
      toast.error("Failed to retrain model", {
        description: message,
      });
    }
  };

  const handleRetrainAll = async () => {
    try {
      const result = await retrainAllModels();
      await Promise.all([refreshModels(), refreshOverview()]);

      const failureMap = Object.fromEntries(
        result.failed.map((item) => [item.ticker.toUpperCase(), item.error])
      );
      setLastRetrainFailures(failureMap);

      const queued =
        result.trained_count === 0 &&
        result.failed_count === 0 &&
        result.message.toLowerCase().includes("queued");

      if (queued) {
        toast.success("Retraining queued", {
          description: result.message,
        });
        return;
      }

      if (result.failed_count > 0) {
        const failedTickers = result.failed.map((item) => item.ticker).join(", ");
        toast.error(`Retrain completed with ${result.failed_count} failure(s)`, {
          description: failedTickers,
        });
        return;
      }

      setLastRetrainFailures({});
      toast.success("Retraining all tracked models", {
        description: `${result.trained_count} ticker(s) trained successfully.`,
      });
    } catch (error) {
      toast.error("Failed to start retraining", {
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    }
  };

  const summary = overview?.summary;

  return (
    <DashboardLayout title="Model Registry">
      <div className="space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Global Model Registry
            </h1>
            <p className="max-w-2xl text-muted-foreground">
              Track every ticker your portfolios depend on, see which models are
              trained, and spot missing coverage before the agent runs.
            </p>
          </div>
          <Button
            onClick={handleRetrainAll}
            disabled={isAnyRetraining || trackedTickers.length === 0}
          >
            {isAnyRetraining ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Retraining...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" />
                Retrain All Tracked Tickers
              </>
            )}
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {isOverviewLoading || !summary ? (
            Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-28" />
            ))
          ) : (
            <>
              <SummaryCard
                icon={Layers3}
                label="Tracked Tickers"
                value={summary.tracked_tickers}
              />
              <SummaryCard
                icon={Workflow}
                label="Portfolio Links"
                value={summary.referenced_portfolios}
              />
              <SummaryCard
                icon={Brain}
                label="Trained Models"
                value={summary.trained_model_count}
              />
              <SummaryCard
                icon={Sparkles}
                label="Fully Covered"
                value={summary.fully_trained_tickers}
              />
              <SummaryCard
                icon={Activity}
                label="Missing Slots"
                value={summary.missing_model_count}
                tone={summary.missing_model_count > 0 ? "warning" : "neutral"}
              />
            </>
          )}
        </div>

        <Card className="border-border/50 bg-card/50">
          <CardHeader>
            <CardTitle>Coverage by ticker</CardTitle>
            <CardDescription>
              Every tracked ticker should have both an LSTM and an XGBoost
              model available.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isOverviewLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-24" />
                ))}
              </div>
            ) : !overview || overview.coverage.length === 0 ? (
              <EmptyState
                icon={Brain}
                title="No tracked tickers yet"
                description="Create a portfolio or add tickers to start building the model registry."
              >
                <Button asChild>
                  <Link href="/portfolios/new">Create Portfolio</Link>
                </Button>
              </EmptyState>
            ) : (
              <div className="space-y-3">
                {overview.coverage.map((item) => {
                  const tickerError =
                    lastRetrainFailures[item.ticker] ?? item.last_training_error;
                  return (
                  <div
                    key={item.ticker}
                    className="rounded-xl border border-border/60 bg-background/60 p-4"
                  >
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div className="space-y-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-lg font-semibold text-foreground">
                            {item.ticker}
                          </span>
                          <Badge
                            variant="outline"
                            className={cn(
                              item.is_fully_trained
                                ? "border-profit/30 bg-profit/10 text-profit"
                                : "border-warning/30 bg-warning/10 text-warning"
                            )}
                          >
                            {item.is_fully_trained ? "Fully trained" : "Needs attention"}
                          </Badge>
                          <Badge variant="outline">
                            {Math.round(item.coverage_pct)}% coverage
                          </Badge>
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {item.portfolios.map((portfolio) => (
                            <Button
                              key={portfolio.id}
                              variant="outline"
                              size="sm"
                              asChild
                            >
                              <Link href={`/dashboard/${portfolio.id}/models`}>
                                {portfolio.name}
                              </Link>
                            </Button>
                          ))}
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {item.trained_model_types.map((modelType) => (
                            <Badge
                              key={`${item.ticker}-${modelType}`}
                              variant="outline"
                              className="border-profit/30 bg-profit/10 text-profit"
                            >
                              {MODEL_TYPES[modelType]}
                            </Badge>
                          ))}
                          {item.missing_model_types.map((modelType) => (
                            <Badge
                              key={`${item.ticker}-${modelType}-missing`}
                              variant="outline"
                              className="border-warning/30 bg-warning/10 text-warning"
                            >
                              Missing {MODEL_TYPES[modelType]}
                            </Badge>
                          ))}
                        </div>

                        {tickerError ? (
                          <p className="text-sm text-loss">
                            Last retrain error: {tickerError}
                          </p>
                        ) : null}

                        {!item.is_fully_trained ? (
                          <div>
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={isRetraining(item.ticker)}
                              onClick={() => handleRetrain(item.ticker)}
                            >
                              {isRetraining(item.ticker) ? (
                                <>
                                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                                  Retrying...
                                </>
                              ) : (
                                <>
                                  <RefreshCw className="h-3.5 w-3.5" />
                                  Retry This Ticker
                                </>
                              )}
                            </Button>
                          </div>
                        ) : null}
                      </div>

                      <div className="text-sm text-muted-foreground">
                        {item.last_trained_at ? (
                          <div className="flex items-center gap-2">
                            <span>Last trained</span>
                            <RelativeDate value={item.last_trained_at} fallbackMode="long" />
                          </div>
                        ) : (
                          <span>No completed training yet</span>
                        )}
                      </div>
                    </div>
                  </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              Registered trained models
            </h2>
            <p className="text-muted-foreground">
              These are the actual model records currently available to the
              agent runtime.
            </p>
          </div>

          {isModelsLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-64" />
              ))}
            </div>
          ) : models.length === 0 ? (
            <Card className="border-border/50 bg-card/50">
              <CardContent className="py-12">
                <EmptyState
                  icon={Brain}
                  title="No trained models registered"
                  description="As soon as model training finishes, the registry will populate here."
                />
              </CardContent>
            </Card>
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
      </div>
    </DashboardLayout>
  );
}

interface SummaryCardProps {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: number;
  tone?: "neutral" | "warning";
}

function SummaryCard({
  icon: Icon,
  label,
  value,
  tone = "neutral",
}: SummaryCardProps) {
  return (
    <Card className="border-border/50 bg-card/50">
      <CardContent className="flex items-center gap-4 p-5">
        <div
          className={cn(
            "flex h-11 w-11 items-center justify-center rounded-xl",
            tone === "warning" ? "bg-warning/10 text-warning" : "bg-primary/10 text-primary"
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold text-foreground">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
